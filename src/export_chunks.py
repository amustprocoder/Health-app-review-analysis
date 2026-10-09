"""
Export per-app review chunks for LLM labelling when no API key is available (labelling is
then done by Claude subagents reading the files directly).

Each app gets data/llm_chunks/<app_id>.jsonl with the newest N reviews (content_len >= 3),
always including that app's validation-sample reviews so validate.py can score the result.

    python src/export_chunks.py --per-app 1000
"""

import argparse
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "reviews.duckdb"
OUT = ROOT / "data" / "llm_chunks"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-app", type=int, default=1000)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    apps = con.execute("SELECT app_id, name FROM apps").fetchall()
    total = 0
    for app_id, name in apps:
        rows = con.execute("""
            WITH v AS (SELECT review_id FROM validation_sample)
            SELECT r.review_id, r.score, r.content
            FROM reviews r
            WHERE r.app_id = ? AND r.content_len >= 3
            ORDER BY (r.review_id IN (SELECT review_id FROM v)) DESC, r.reviewed_at DESC
            LIMIT ?""", [app_id, args.per_app]).fetchall()
        path = OUT / f"{app_id}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for i, (rid, score, text) in enumerate(rows):
                fh.write(json.dumps({"n": i, "id": rid, "score": score, "text": text.replace("\n", " ")[:500]},
                                    ensure_ascii=False) + "\n")
        total += len(rows)
        print(f"{name:15s} {len(rows):5d} -> {path.name}")
    print(f"{total} reviews exported to {OUT}")


if __name__ == "__main__":
    main()
