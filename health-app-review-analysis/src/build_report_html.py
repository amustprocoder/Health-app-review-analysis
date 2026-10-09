"""
Build output/findings.html: a self-contained, shareable version of the findings
(charts embedded as data URIs, tables from the query CSVs).

    python src/build_report_html.py
"""

import base64
import html
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
CHARTS = OUT / "charts"


def img(name: str, alt: str) -> str:
    b64 = base64.standard_b64encode((CHARTS / name).read_bytes()).decode("ascii")
    return f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(alt)}"><figcaption>{html.escape(alt)}</figcaption></figure>'


def table(df: pd.DataFrame, cols: list, rename: dict | None = None, n: int | None = None) -> str:
    d = df[cols].head(n) if n else df[cols]
    if rename:
        d = d.rename(columns=rename)
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in d.columns)
    rows = []
    for _, r in d.iterrows():
        cells = []
        for v in r:
            if pd.isna(v):
                cells.append("<td></td>")
            elif isinstance(v, float):
                cells.append(f'<td class="num">{v:,.1f}</td>')
            elif isinstance(v, int):
                cells.append(f'<td class="num">{v:,}</td>')
            else:
                cells.append(f"<td>{html.escape(str(v))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def main() -> None:
    mix = pd.read_csv(OUT / "01_complaint_mix_by_app.csv")
    cat = pd.read_csv(OUT / "02_category_wide.csv")
    rel = pd.read_csv(OUT / "03_before_after_release.csv")
    rat = pd.read_csv(OUT / "04_rating_and_upvotes_by_label.csv")
    ig = pd.read_csv(OUT / "06_india_vs_global.csv")
    val_llm = pd.read_csv(OUT / "validation_llm.csv")
    apps = mix.drop_duplicates("app")[["app", "segment", "n_reviews", "complaint_rate_pct", "avg_rating"]]
    top3 = (mix[mix["rank_in_app"] <= 3].groupby("app")
            .apply(lambda g: ", ".join(f"{r.label} {r.pct_of_complaints:.0f}%" for r in g.itertuples()))
            .rename("top 3 complaints").reset_index())
    apps = apps.merge(top3, on="app").sort_values("complaint_rate_pct", ascending=False)
    apps["n_reviews"] = apps["n_reviews"].astype(int)

    fs = rel[rel["app"] == "FatSecret"].sort_values("release_proxy_date")
    fs_tbl = table(fs, ["app_version", "release_proxy_date", "n_before", "n_after", "rating_before", "rating_after",
                        "complaint_pct_before", "complaint_pct_after", "ux_pct_before", "ux_pct_after", "mentions_update_pct_after"],
                   {"app_version": "version", "release_proxy_date": "first seen", "n_before": "reviews before", "n_after": "reviews after",
                    "rating_before": "stars before", "rating_after": "stars after", "complaint_pct_before": "complaint % before",
                    "complaint_pct_after": "complaint % after", "ux_pct_before": "UX % before", "ux_pct_after": "UX % after",
                    "mentions_update_pct_after": "% blame update"})
    good = rel.sort_values("complaint_delta_pp").head(5)

    page = f"""<title>Health App Complaints India</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
/* layout: single reading column, wide figures break out slightly; tables scroll in their own box */
:root {{
  --bg: #faf8f4; --fg: #1f2320; --muted: #5f655f; --rule: #d9d4c8; --accent: #0f6b66; --accent-soft: #e2efed;
  --warn: #b4451c; --tile: #f1ede4;
  --display: "Source Serif 4", Georgia, "Times New Roman", serif;
  --body: "IBM Plex Sans", "Segoe UI", Roboto, Arial, sans-serif;
  --mono: "IBM Plex Mono", Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #15181a; --fg: #e8e6df; --muted: #a2a69e; --rule: #33393a; --accent: #5fc5bd; --accent-soft: #1d302f;
  --warn: #e3875f; --tile: #1d2124; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #15181a; --fg: #e8e6df; --muted: #a2a69e; --rule: #33393a; --accent: #5fc5bd; --accent-soft: #1d302f;
  --warn: #e3875f; --tile: #1d2124; color-scheme: dark }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 16px; line-height: 1.55; margin: 0; }}
.wrap {{ max-width: 760px; margin: 0 auto; padding-block: 40px 80px; padding-inline: 20px; }}
h1, h2, h3 {{ font-family: var(--display); font-weight: 600; line-height: 1.15; text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(30px, 5vw, 42px); }}
h2 {{ font-size: 26px; margin-top: 56px; padding-top: 18px; border-top: 1px solid var(--rule); }}
h3 {{ font-size: 19px; margin-top: 30px; }}
p {{ margin: 14px 0; max-width: 66ch; }}
.eyebrow {{ font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); font-weight: 600; margin-bottom: 14px; }}
.lede {{ font-size: 18px; color: var(--muted); max-width: 62ch; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 28px 0; }}
.tile {{ background: var(--tile); padding: 14px 16px; border-radius: 6px; min-width: 0; }}
.tile b {{ display: block; font-family: var(--display); font-size: 30px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.tile span {{ font-size: 13px; color: var(--muted); }}
.note {{ background: var(--accent-soft); border-left: 3px solid var(--accent); padding: 12px 16px; margin: 22px 0; font-size: 15px; }}
.note p {{ margin: 6px 0; }}
.tablewrap {{ overflow-x: auto; margin: 18px 0; border: 1px solid var(--rule); border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--rule); vertical-align: top; }}
th {{ font-size: 12px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); font-size: 13px; }}
tbody tr:last-child td {{ border-bottom: 0; }}
figure {{ margin: 24px 0; }}
figure img {{ max-width: 100%; border-radius: 4px; border: 1px solid var(--rule); background: #fff; }}
figcaption {{ font-size: 13px; color: var(--muted); margin-top: 6px; }}
ul {{ padding-left: 20px; }} li {{ margin: 6px 0; max-width: 66ch; }}
code {{ font-family: var(--mono); font-size: 13px; background: var(--tile); padding: 1px 5px; border-radius: 3px; }}
.method {{ font-size: 15px; color: var(--muted); }}
a {{ color: var(--accent); }}
@media (max-width: 480px) {{ body {{ font-size: 15px; }} h2 {{ font-size: 23px; }} }}
</style>
<div class="wrap">
<div class="eyebrow">Comparative review study, India Play Store, October 2026</div>
<h1>What 120,000 Indian users complain about in health and nutrition apps</h1>
<p class="lede">Fifteen apps, one complaint label per review, seven SQL questions, and a validation step before any number was written. The biggest complaint in the category turns out to be self-inflicted.</p>

<div class="tiles">
  <div class="tile"><b>119,266</b><span>text reviews scraped, 15 apps</span></div>
  <div class="tile"><b>15,000</b><span>newest reviews classified by LLM</span></div>
  <div class="tile"><b>93.3%</b><span>classifier accuracy on 300 reference labels, κ 0.92</span></div>
  <div class="tile"><b>22%</b><span>of all complaints are about UX and redesigns</span></div>
</div>

<div class="note">
<p><strong>How to read the numbers.</strong> The newest 1,000 reviews per app were labelled by an LLM classifier (Claude Sonnet) into a 16-label taxonomy. Before any analysis, both that classifier and a keyword baseline were scored against 300 reviews (20 per app) labelled independently, one at a time, by a different model (Claude Fable). LLM: 93.3% accuracy, Cohen's κ 0.92. Keyword baseline: 51.7%, κ 0.45. A human spot-check of the reference labels is the open item.</p>
<p>The baseline did not just score lower; it told a different story. On keyword labels the top complaint looked like the food database (precision 0.25 on that label). On validated labels it is the redesign. That gap is why the validation step exists.</p>
</div>

<h2>The one finding: redesigns are the #1 complaint</h2>
<p>UX is the largest complaint across the 15 apps: 22% of all complaints and a top-3 complaint in 11 of 15 apps. It is also the one users agree on most. UX reviews collect 23% of every "helpful" vote in the set, almost as many as all praise combined (25%), at 2.5 votes per review against 1.6 for paywall and crash complaints. And 44% of UX complaints explicitly blame an update, against 2% for paywall and 6% for food-database complaints. This is not "the app is confusing". It is "the app was fine and you changed it".</p>

<div class="tablewrap"><table><thead><tr><th>App</th><th>UX share of complaints</th><th>UX reviews that blame an update</th></tr></thead><tbody>
<tr><td>MyFitnessPal</td><td class="num">40%</td><td class="num">85%</td></tr>
<tr><td>FatSecret</td><td class="num">38%</td><td class="num">65%</td></tr>
<tr><td>YAZIO</td><td class="num">36%</td><td class="num">15%</td></tr>
<tr><td>Samsung Health</td><td class="num">28%</td><td class="num">72%</td></tr>
<tr><td>Lifesum</td><td class="num">26%</td><td class="num">52%</td></tr>
<tr><td>MyNetDiary</td><td class="num">22%</td><td class="num">12%</td></tr>
</tbody></table></div>

<p>Four apps shipped a redesign inside the window and all four show the same signature:</p>
<ul>
<li><strong>MyFitnessPal</strong> (new layout, spring 2026): 40% of its complaints are UX, 85% of those name the update, and the most upvoted review in the set reads the change as a nudge toward premium.</li>
<li><strong>FatSecret 11.8.0.5</strong> (new food-logging UI, first seen 27 Aug 2026): complaint rate 24% to 54% in the 30 days after vs the 30 before, average rating 4.28 to 3.28, UX share 6% to 35%, 37% of post-release reviews blaming the update. The follow-up 11.8.0.6 two weeks later pulled the complaint rate back to 29% and the rating to 4.5.</li>
<li><strong>Samsung Health 7.00.6</strong> (new home screen, Sep 2026): 72% of its UX complaints cite the update.</li>
<li><strong>Lifesum</strong> (new design plus AI-first logging): 52% of UX complaints cite the update.</li>
</ul>
<p>The common thread: a feature or layout people used daily was moved, hidden or replaced (meal copy, "done logging", quick add, dashboard widgets, the old diary), and the change was read as a push toward premium. YAZIO is the exception that proves the rule: its 36% UX share is onboarding friction (endless questionnaires, spin-the-wheel animations), not one release, which is why only 15% cite an update.</p>

<h3>FatSecret, release by release</h3>
<p>The cleanest natural experiment in the set. Window: 30 days before vs 30 days after the first review seen on each version.</p>
{fs_tbl}

{img("complaint_mix_by_app.png", "What users complain about, per app (LLM labels, newest 1,000 reviews each)")}

<h2>Four more things the data says</h2>
<p><strong>"Not free" is the second complaint, and it is an onboarding problem more than a pricing one.</strong> Paywall is 19% of complaints and top-3 in 8 of 15 apps: Lose It! 44%, Cronometer 37%, BodyFast 36%, MyNetDiary 32%, Cal AI 27%, HealthifyMe 26%. The dominant pattern in the text is "filled in the whole questionnaire, then hit the price screen". Showing the price before the setup flow is a copy change, not a pricing change.</p>
<p><strong>Global apps lose Indian users on redesigns and price; Indian apps lose them on service.</strong> India-built apps (HealthifyMe, FITTR, Fitelo, cult.fit) vs global trackers: coach and support 17% vs 1%, UX 10% vs 25%, paywall 12% vs 24%, food database 4% vs 12%, crashes 19% vs 14%. The Indian apps sell a human; the human is what gets reviewed.</p>
{img("india_vs_global.png", "India-built coaching apps vs global trackers: complaint mix")}
<p><strong>The food database is unsolved, and it is a tracker problem, not a category problem.</strong> 9% of all complaints, but 32% at FatSecret, 23% at Lifesum, 16% at Cal AI (the AI-photo app built to replace the database), 14% at Cronometer, 13% at Noom and MyNetDiary. It never reaches the top 3 at the coaching apps, where a human writes the plan.</p>
<p><strong>Billing and support complaints are small but lethal.</strong> Billing is 4.5% of complaints but 88% of them are 1-star (average 1.20, the lowest of any label); coach and support complaints are 86% 1-star. UX complaints, for all their volume, average 2.0 stars. A redesign costs ratings broadly; a billing failure costs the customer.</p>
{img("rating_by_label.png", "Average star rating of reviews carrying each complaint")}
<p><strong>Releases cut both ways, and the fixes are invisible.</strong> The five releases that reduced complaints most dropped the complaint rate by 20 to 65 points and lifted ratings by 0.7 to 2.1 stars within 30 days, and almost nobody wrote "thanks for the update". Users write when things break.</p>
{table(good, ["app", "app_version", "release_proxy_date", "n_before", "n_after", "rating_before", "rating_after", "complaint_pct_before", "complaint_pct_after"],
       {"app_version": "version", "release_proxy_date": "first seen", "n_before": "reviews before", "n_after": "reviews after", "rating_before": "stars before", "rating_after": "stars after", "complaint_pct_before": "complaint % before", "complaint_pct_after": "complaint % after"})}

<h2>Per app</h2>
{table(apps, ["app", "segment", "n_reviews", "complaint_rate_pct", "avg_rating", "top 3 complaints"],
       {"n_reviews": "reviews", "complaint_rate_pct": "complaint %", "avg_rating": "avg stars"})}
{img("complaint_rate_by_app.png", "Share of the newest 1,000 reviews that are complaints, per app")}

<h2>Category-wide vs app-specific</h2>
<p><code>apps where top 3</code> is the number of the 15 apps where this is a top-3 complaint. A high average share with low spread is a category problem; a high maximum with high spread is one app's problem.</p>
{table(cat[cat["label"] != "no_complaint"], ["label", "total_complaints", "pct_of_all_complaints", "apps_where_top3", "avg_share_pct", "min_share_pct", "max_share_pct", "stddev_share_pct", "worst_app"],
       {"total_complaints": "n", "pct_of_all_complaints": "% of all", "apps_where_top3": "apps where top 3", "avg_share_pct": "avg share %", "min_share_pct": "min", "max_share_pct": "max", "stddev_share_pct": "spread", "worst_app": "highest at"})}
{img("category_wide_vs_specific.png", "Average share across apps vs spread; bubble size is volume")}

<h2>What a PM at one of these apps could do with this</h2>
<ul>
<li><strong>Anyone planning a redesign:</strong> the FatSecret 11.8.0.5 to 11.8.0.6 pair shows 30 points of complaint rate in two weeks, then back. Ship layout changes behind a "use the old layout" switch and watch the share of reviews that blame an update, not just the star rating; the rating lags, the blame does not.</li>
<li><strong>Global trackers (MyFitnessPal, Lose It!, Lifesum, FatSecret):</strong> two fixes cover half the complaints: show the price before the questionnaire, and keep the diary flow stable. The Indian-food database gap is third.</li>
<li><strong>Indian coaching apps (HealthifyMe, Fitelo, FITTR):</strong> coach responsiveness is the product. Fitelo's 28% coach share is a capacity or SLA problem; HealthifyMe's upsell-pressure reviews are a sales-incentive problem.</li>
<li><strong>Samsung Health:</strong> tracking 24%, device sync 12%, UX 28%: the watch-plus-app system is reviewed as one product, and the app takes the blame for the hardware.</li>
</ul>

<h2>Method</h2>
<p class="method">Reviews scraped with google-play-scraper (India store, English locale, newest 8,000 per app) on 2 October 2026 and loaded into DuckDB. Each review gets one primary label from a 16-label taxonomy (billing, paywall, login, crash, performance, food_db, tracking, device_sync, coach_support, spam, ux, content_quality, privacy, localisation, other_complaint, no_complaint), plus whether it blames an update and a 1 to 3 severity. Two classifiers write to the same table: a regex baseline over all 119,266 reviews and an LLM classifier over the newest 1,000 per app. Both were scored against 300 reference-labelled reviews (stratified 12 low, 3 mid, 5 high rating per app). All analysis runs as SQL against DuckDB; the exact queries are published with the repository. Release dates are a proxy (first review seen on a version); before/after windows are 30 days each and keep only versions with 50+ reviews on both sides.</p>
<h3>Classifier validation, per label (LLM)</h3>
{table(val_llm[val_llm["n_human"] > 0], ["label", "n_human", "precision", "recall", "f1"], {"n_human": "n (reference)"})}
<h3>Limits</h3>
<p class="method">Play Store text reviews over-represent angry users; this is the mix among complainers, not among users. LLM labels cover the newest 1,000 reviews per app, so the time window differs by app (MyFitnessPal and Samsung Health: the last 10 months; Fitelo and FITTR: several years). The reference labels are model annotations until the human spot-check is done. The India-store scrape still returns some non-Indian, non-English reviews; fewer than 1% are Hindi or Hinglish by a script heuristic, so no language comparison is made.</p>
</div>
"""
    (OUT / "findings.html").write_text(page, encoding="utf-8")
    print(f"wrote {OUT / 'findings.html'} ({(OUT / 'findings.html').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
