"""
Load data/raw/*.jsonl into DuckDB (data/reviews.duckdb).

Tables:
  apps      app_id, name, segment, title, score, ratings, installs, version
  reviews   review_id, app_id, score, content, thumbs_up, app_version, at, replied_at, reply_content,
            year_month, content_len, lang_hint
  releases  app_id, app_version, first_seen, last_seen, n_reviews   (release proxy: first review on a version)

Run: python src/build_db.py
"""

import json
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apps import APPS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "reviews.duckdb"

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINGLISH = re.compile(r"\b(?:hai|nahi|nhi|kya|bahut|bhut|acha|accha|achha|mera|mere|kar|karo|karna|paisa|paise|"
                      r"bakwas|bekar|bekaar|wapas|refund\s*nahi|chalta|chal|bhi|aur|lekin|par|se|ko|ka|ki|ke)\b", re.I)


def lang_hint(text: str) -> str:
    if DEVANAGARI.search(text):
        return "hi"
    if len(HINGLISH.findall(text)) >= 2:
        return "hinglish"
    return "en"


def main() -> None:
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    meta = json.loads((RAW / "app_meta.json").read_text(encoding="utf-8")) if (RAW / "app_meta.json").exists() else {}
    con.execute("""CREATE TABLE apps (app_id VARCHAR PRIMARY KEY, name VARCHAR, segment VARCHAR, title VARCHAR,
                   score DOUBLE, ratings BIGINT, installs VARCHAR, version VARCHAR)""")
    for app_id, name, segment, _cap in APPS:
        m = meta.get(app_id, {})
        con.execute("INSERT INTO apps VALUES (?,?,?,?,?,?,?,?)",
                    [app_id, name, segment, m.get("title"), m.get("score"), m.get("ratings"), m.get("installs"), m.get("version")])

    con.execute("""CREATE TABLE reviews (review_id VARCHAR PRIMARY KEY, app_id VARCHAR, score INTEGER, content VARCHAR,
                   thumbs_up INTEGER, app_version VARCHAR, reviewed_at TIMESTAMP, replied_at TIMESTAMP, reply_content VARCHAR,
                   year_month VARCHAR, content_len INTEGER, lang_hint VARCHAR)""")
    rows = []
    for f in sorted(RAW.glob("*.jsonl")):
        for line in f.open(encoding="utf-8"):
            r = json.loads(line)
            txt = (r.get("content") or "").strip()
            rows.append([r["reviewId"], r["app_id"], int(r["score"]), txt, int(r.get("thumbsUpCount") or 0),
                         r.get("appVersion"), r["at"], r.get("repliedAt"), r.get("replyContent"),
                         r["at"][:7], len(txt), lang_hint(txt)])
    import pandas as pd
    df = pd.DataFrame(rows, columns=["review_id", "app_id", "score", "content", "thumbs_up", "app_version", "reviewed_at",
                                     "replied_at", "reply_content", "year_month", "content_len", "lang_hint"])
    df["reviewed_at"] = pd.to_datetime(df["reviewed_at"])
    df["replied_at"] = pd.to_datetime(df["replied_at"])
    df = df.drop_duplicates("review_id")
    con.execute("INSERT INTO reviews SELECT * FROM df")      # bulk insert via DuckDB's pandas scan

    con.execute("""CREATE TABLE releases AS
                   SELECT app_id, app_version, MIN(reviewed_at) AS first_seen, MAX(reviewed_at) AS last_seen, COUNT(*) AS n_reviews
                   FROM reviews WHERE app_version IS NOT NULL AND app_version <> ''
                   GROUP BY app_id, app_version HAVING COUNT(*) >= 20""")
    n = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    per_app = con.execute("SELECT a.name, COUNT(*) n, ROUND(AVG(r.score),2) avg_score FROM reviews r JOIN apps a USING(app_id) "
                          "GROUP BY 1 ORDER BY 2 DESC").fetchall()
    print(f"{n} reviews loaded into {DB}")
    for name, cnt, avg in per_app:
        print(f"  {name:15s} {cnt:6d}  avg {avg}")
    print("date range:", con.execute("SELECT MIN(reviewed_at), MAX(reviewed_at) FROM reviews").fetchone())
    print("lang:", con.execute("SELECT lang_hint, COUNT(*) FROM reviews GROUP BY 1").fetchall())
    con.close()


if __name__ == "__main__":
    main()
