"""
Draw the 300-review validation sample for hand labelling.

Stratified: 20 per app (15 apps = 300), within each app weighted toward low ratings
(complaints are what the taxonomy is for) but keeping 5-star reviews so the no_complaint
boundary gets tested too. Fixed seed so the sample is reproducible.

    python src/sample_for_validation.py
Writes validation/to_label.csv (fill the `human_label` column by hand) and registers the
sample in DuckDB as table validation_sample.
"""

import csv
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "reviews.duckdb"
OUT = ROOT / "validation" / "to_label.csv"
PER_APP = 20
SEED = 42


def main() -> None:
    con = duckdb.connect(str(DB))
    con.execute(f"SELECT setseed({SEED / 100})")
    rows = con.execute(f"""
        WITH ranked AS (
            SELECT r.review_id, a.name AS app, r.score, r.content, r.reviewed_at, r.app_version, r.lang_hint,
                   CASE WHEN r.score <= 2 THEN 'low' WHEN r.score = 3 THEN 'mid' ELSE 'high' END AS bucket,
                   row_number() OVER (PARTITION BY r.app_id,
                        CASE WHEN r.score <= 2 THEN 'low' WHEN r.score = 3 THEN 'mid' ELSE 'high' END
                        ORDER BY random()) AS rn
            FROM reviews r JOIN apps a USING (app_id)
            WHERE r.content_len >= 15
        )
        SELECT review_id, app, score, content, reviewed_at, app_version, lang_hint, bucket
        FROM ranked
        WHERE (bucket = 'low' AND rn <= 12) OR (bucket = 'mid' AND rn <= 3) OR (bucket = 'high' AND rn <= 5)
        ORDER BY app, score, review_id
    """).fetchall()
    con.execute("CREATE OR REPLACE TABLE validation_sample AS SELECT * FROM (VALUES " +
                ",".join(f"('{r[0]}')" for r in rows) + ") t(review_id)")
    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists():
        print(f"{OUT} already exists; not overwriting hand labels. Delete it to redraw.")
    else:
        with OUT.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["review_id", "app", "score", "lang_hint", "app_version", "reviewed_at", "content",
                        "human_label", "human_severity", "human_notes"])
            for r in rows:
                w.writerow([r[0], r[1], r[2], r[6], r[5], str(r[4])[:10], r[3].replace("\n", " "), "", "", ""])
        print(f"Wrote {len(rows)} reviews to {OUT}. Label the human_label column using taxonomy.md codes.")
    con.close()


if __name__ == "__main__":
    main()
