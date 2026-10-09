"""
Import LLM labels produced outside classify.py (e.g. by Claude subagents reading
data/llm_chunks/*.jsonl) into the `labels` table as classifier='llm'.

Expects data/llm_labels/<app_id>.csv with header: n,label,mentions_update,severity
(n = the review's index in the matching chunk file). Rows with unknown labels are skipped
and reported; coverage per app is printed so gaps are visible.

    python src/import_llm_labels.py --model claude-sonnet-5-5
"""

import argparse
import csv
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "reviews.duckdb"
CHUNKS = ROOT / "data" / "llm_chunks"
LABELS_DIR = ROOT / "data" / "llm_labels"
VALID = {"billing", "paywall", "login", "crash", "performance", "food_db", "tracking", "device_sync",
         "coach_support", "spam", "ux", "content_quality", "privacy", "localisation", "other_complaint", "no_complaint"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-subagent")
    args = ap.parse_args()
    con = duckdb.connect(str(DB))
    con.execute("""CREATE TABLE IF NOT EXISTS labels (review_id VARCHAR, classifier VARCHAR, label VARCHAR,
                   is_complaint BOOLEAN, mentions_update BOOLEAN, severity INTEGER, model VARCHAR,
                   PRIMARY KEY (review_id, classifier))""")
    rows, bad = [], 0
    for chunk in sorted(CHUNKS.glob("*.jsonl")):
        app_id = chunk.stem
        lab_path = LABELS_DIR / f"{app_id}.csv"
        if not lab_path.exists():
            print(f"{app_id}: no labels file")
            continue
        ids = {}
        for line in chunk.open(encoding="utf-8"):
            d = json.loads(line)
            ids[int(d["n"])] = d["id"]
        got = 0
        for r in csv.DictReader(lab_path.open(encoding="utf-8")):
            try:
                n = int(r["n"])
            except (ValueError, TypeError):
                bad += 1
                continue
            lab = (r.get("label") or "").strip().lower()
            lab = {"nc": "no_complaint", "none": "no_complaint", "other": "other_complaint", "coach": "coach_support",
                   "content": "content_quality", "sync": "device_sync", "perf": "performance"}.get(lab, lab)
            if n not in ids or lab not in VALID:
                bad += 1
                continue
            mu = str(r.get("mentions_update", "")).strip().lower() in ("1", "true", "yes", "y")
            try:
                sev = max(1, min(3, int(float(r.get("severity") or 1))))
            except ValueError:
                sev = 1
            rows.append([ids[n], "llm", lab, lab != "no_complaint", mu, sev, args.model])
            got += 1
        print(f"{app_id}: {got}/{len(ids)} labelled")
    if rows:
        df = pd.DataFrame(rows, columns=["review_id", "classifier", "label", "is_complaint", "mentions_update", "severity", "model"])
        df = df.drop_duplicates("review_id")
        con.execute("INSERT OR REPLACE INTO labels SELECT * FROM df")
        con.commit()
    print(f"imported {len(rows)} llm labels ({bad} rows skipped)")
    print(con.execute("SELECT label, COUNT(*) FROM labels WHERE classifier='llm' GROUP BY 1 ORDER BY 2 DESC").fetchall())
    con.close()


if __name__ == "__main__":
    main()
