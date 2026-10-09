"""
Score each classifier against the hand labels in validation/to_label.csv.

Reports, per classifier: accuracy, Cohen's kappa, per-label precision / recall / F1, the
confusion pairs that hurt most, and is_complaint accuracy (the binary question most of the
SQL rests on). Only rows with a filled human_label are scored.

    python src/validate.py
Writes output/validation_report.md and output/validation_<classifier>.csv
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import LABELS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "reviews.duckdb"
HUMAN = ROOT / "validation" / "to_label.csv"
OUT = ROOT / "output"


def kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if not n:
        return float("nan")
    agree = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (agree - expected) / (1 - expected) if expected < 1 else 1.0


def main() -> None:
    human = {}
    for r in csv.DictReader(HUMAN.open(encoding="utf-8")):
        lab = (r.get("human_label") or "").strip().lower()
        if lab:
            if lab not in LABELS:
                print(f"  WARNING unknown label '{lab}' on {r['review_id']} (see taxonomy.md)")
                continue
            human[r["review_id"]] = lab
    if not human:
        raise SystemExit(f"No hand labels yet. Fill human_label in {HUMAN} first (codes in taxonomy.md).")
    print(f"{len(human)} hand-labelled reviews")

    con = duckdb.connect(str(DB), read_only=True)
    classifiers = [c[0] for c in con.execute("SELECT DISTINCT classifier FROM labels").fetchall()]
    md = ["# Classifier validation against reference labels", "",
          f"Reference-labelled reviews: **{len(human)}** (see validation/apply_reference_labels.py for who labelled them and how)", ""]
    OUT.mkdir(exist_ok=True)
    for clf in classifiers:
        pred = dict(con.execute("SELECT review_id, label FROM labels WHERE classifier = ?", [clf]).fetchall())
        pairs = [(human[rid], pred[rid]) for rid in human if rid in pred]
        if not pairs:
            md.append(f"## {clf}: no overlap with hand labels yet (run classify.py --only-validation)")
            continue
        acc = sum(1 for a, b in pairs if a == b) / len(pairs)
        k = kappa(pairs)
        bin_pairs = [(a != "no_complaint", b != "no_complaint") for a, b in pairs]
        bin_acc = sum(1 for a, b in bin_pairs if a == b) / len(bin_pairs)
        tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
        conf = Counter()
        for a, b in pairs:
            if a == b:
                tp[a] += 1
            else:
                fp[b] += 1; fn[a] += 1; conf[(a, b)] += 1
        rows = []
        for lab in LABELS:
            p = tp[lab] / (tp[lab] + fp[lab]) if tp[lab] + fp[lab] else None
            r = tp[lab] / (tp[lab] + fn[lab]) if tp[lab] + fn[lab] else None
            f1 = 2 * p * r / (p + r) if p and r else (0.0 if (p is not None and r is not None) else None)
            rows.append({"label": lab, "n_human": tp[lab] + fn[lab], "precision": p, "recall": r, "f1": f1})
        with (OUT / f"validation_{clf}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
        print(f"\n== {clf}: n={len(pairs)} accuracy={acc:.1%} kappa={k:.2f} is_complaint accuracy={bin_acc:.1%}")
        md += [f"## {clf}", "", f"- Reviews scored: **{len(pairs)}**", f"- Accuracy (exact label): **{acc:.1%}**",
               f"- Cohen's kappa: **{k:.2f}**", f"- Complaint vs no-complaint accuracy: **{bin_acc:.1%}**", "",
               "| Label | n (human) | Precision | Recall | F1 |", "|---|---|---|---|---|"]
        for r in rows:
            if r["n_human"] or r["precision"] is not None:
                f = lambda x: "-" if x is None else f"{x:.2f}"
                md.append(f"| {r['label']} | {r['n_human']} | {f(r['precision'])} | {f(r['recall'])} | {f(r['f1'])} |")
                print(f"  {r['label']:16s} n={r['n_human']:3d} P={f(r['precision'])} R={f(r['recall'])} F1={f(r['f1'])}")
        md += ["", "Most common confusions (human -> model):", ""]
        for (a, b), n in conf.most_common(8):
            md.append(f"- {a} -> {b}: {n}")
            print(f"  confusion {a} -> {b}: {n}")
        md.append("")
    (OUT / "validation_report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nReport: {OUT / 'validation_report.md'}")


if __name__ == "__main__":
    main()
