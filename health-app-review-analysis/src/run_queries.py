"""
Run every sql/*.sql against data/reviews.duckdb, save CSVs, draw the charts.

    python src/run_queries.py                  # uses llm labels if present, else keyword
    python src/run_queries.py --classifier keyword

Outputs: output/<query>.csv, output/charts/*.png, output/query_log.md (each SQL + row count)
"""

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "reviews.duckdb"
SQL = ROOT / "sql"
OUT = ROOT / "output"
CHARTS = OUT / "charts"


def run_all(classifier: str) -> dict[str, pd.DataFrame]:
    con = duckdb.connect(str(DB), read_only=True)
    results = {}
    log = [f"# Query log (classifier = {classifier})", ""]
    for f in sorted(SQL.glob("*.sql")):
        sql = f.read_text(encoding="utf-8").replace("{classifier}", classifier)
        df = con.execute(sql).df()
        name = f.stem
        df.to_csv(OUT / f"{name}.csv", index=False)
        results[name] = df
        log += [f"## {name} ({len(df)} rows)", "", "```sql", sql.strip(), "```", ""]
        print(f"{name}: {len(df)} rows -> output/{name}.csv")
    con.close()
    (OUT / "query_log.md").write_text("\n".join(log), encoding="utf-8")
    return results


def charts(res: dict[str, pd.DataFrame], classifier: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

    # 1. stacked complaint mix per app (top 8 labels + other)
    mix = res["01_complaint_mix_by_app"]
    if len(mix):
        top_labels = mix.groupby("label")["n"].sum().sort_values(ascending=False).index[:8].tolist()
        piv = mix.pivot_table(index="app", columns="label", values="pct_of_complaints", aggfunc="sum").fillna(0)
        other = piv.drop(columns=[c for c in top_labels if c in piv.columns]).sum(axis=1)
        piv = piv[[c for c in top_labels if c in piv.columns]]
        piv["other"] = other
        order = mix.drop_duplicates("app").set_index("app")["complaint_rate_pct"].sort_values(ascending=False).index
        piv = piv.loc[[a for a in order if a in piv.index]]
        ax = piv.plot(kind="barh", stacked=True, figsize=(11.5, 6.5), colormap="tab20", width=0.8)
        ax.set_xlabel("% of the app's complaints")
        ax.set_ylabel("")
        ax.invert_yaxis()
        ax.set_title(f"What users complain about, per app (classifier: {classifier})")
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=False)
        plt.tight_layout()
        plt.savefig(CHARTS / "complaint_mix_by_app.png")
        plt.close()

        # 2. complaint rate + rating per app
        rates = mix.drop_duplicates("app").set_index("app")[["complaint_rate_pct", "avg_rating", "n_reviews"]].sort_values("complaint_rate_pct")
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.barh(rates.index, rates["complaint_rate_pct"], color="#c44e52")
        for i, (v, n) in enumerate(zip(rates["complaint_rate_pct"], rates["n_reviews"])):
            ax.text(v + 0.5, i, f"{v:.0f}%  (n={n:,})", va="center", fontsize=7.5)
        ax.set_xlabel("% of text reviews that are complaints")
        ax.set_title("Complaint rate per app")
        plt.tight_layout()
        plt.savefig(CHARTS / "complaint_rate_by_app.png")
        plt.close()

    # 3. category-wide: avg share vs spread
    cat = res["02_category_wide"]
    if len(cat):
        cat = cat[cat["label"] != "no_complaint"]
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.scatter(cat["avg_share_pct"], cat["stddev_share_pct"], s=cat["total_complaints"] / cat["total_complaints"].max() * 600 + 20,
                   alpha=0.6, color="#4c72b0")
        for _, r in cat.iterrows():
            ax.annotate(r["label"], (r["avg_share_pct"], r["stddev_share_pct"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
        ax.set_xlabel("average share of an app's complaints (%)")
        ax.set_ylabel("spread across apps (std dev, pp)")
        ax.set_title("Category-wide (right, low) vs app-specific (high) complaints; bubble = volume")
        plt.tight_layout()
        plt.savefig(CHARTS / "category_wide_vs_specific.png")
        plt.close()

    # 4. india-built vs global
    ig = res["06_india_vs_global"]
    if len(ig):
        ig = ig[ig["label"] != "no_complaint"].set_index("label")[["india_built_pct", "global_pct"]].fillna(0)
        ig = ig.sort_values("india_built_pct", ascending=True)
        ax = ig.plot(kind="barh", figsize=(9, 6), color=["#dd8452", "#4c72b0"], width=0.8)
        ax.set_xlabel("% of complaints")
        ax.set_ylabel("")
        ax.set_title("India-built coaching apps vs global trackers: complaint mix")
        ax.legend(["India-built (Healthify, cult.fit, FITTR, Fitelo)", "Global (MFP, FatSecret, Lose It!, ... )"], frameon=False, fontsize=8)
        plt.tight_layout()
        plt.savefig(CHARTS / "india_vs_global.png")
        plt.close()

    # 5. monthly complaint trend for the 6 biggest apps
    tr = res["05_monthly_trend"]
    if len(tr):
        big = tr.groupby("app")["n"].sum().sort_values(ascending=False).index[:6]
        fig, ax = plt.subplots(figsize=(10, 5))
        for app in big:
            d = tr[tr["app"] == app].sort_values("year_month")
            d = d[d["year_month"] >= "2024-01"]
            if len(d) >= 3:
                ax.plot(d["year_month"], d["complaint_pct"], marker="o", ms=3, label=app)
        ax.set_ylabel("% complaints")
        ax.set_title("Monthly complaint rate (months with 30+ reviews)")
        ax.tick_params(axis="x", rotation=60, labelsize=7)
        ax.legend(fontsize=8, frameon=False, ncol=3)
        plt.tight_layout()
        plt.savefig(CHARTS / "monthly_complaint_trend.png")
        plt.close()

    # 6. rating by label
    rl = res["04_rating_and_upvotes_by_label"]
    if len(rl):
        rl = rl[rl["label"] != "no_complaint"].sort_values("avg_rating")
        fig, ax = plt.subplots(figsize=(8.5, 5))
        ax.barh(rl["label"], rl["avg_rating"], color="#55a868")
        for i, (v, n) in enumerate(zip(rl["avg_rating"], rl["n"])):
            ax.text(v + 0.03, i, f"{v:.2f}  (n={n:,})", va="center", fontsize=7.5)
        ax.set_xlim(1, 5)
        ax.set_xlabel("average star rating of reviews with this complaint")
        ax.set_title("Which complaint costs the most stars")
        plt.tight_layout()
        plt.savefig(CHARTS / "rating_by_label.png")
        plt.close()
    print(f"charts -> {CHARTS}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classifier", choices=["llm", "keyword"])
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    have = {c[0]: c[1] for c in con.execute("SELECT classifier, COUNT(*) FROM labels GROUP BY 1").fetchall()}
    con.close()
    clf = args.classifier or ("llm" if have.get("llm", 0) >= 1000 else "keyword")
    print(f"classifier = {clf} ({have.get(clf, 0)} labelled reviews)")
    res = run_all(clf)
    charts(res, clf)


if __name__ == "__main__":
    main()
