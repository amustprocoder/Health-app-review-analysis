"""
Scrape Play Store reviews for every app in src/apps.py.

Usage:
    python src/scrape_reviews.py                 # all apps, caps from apps.py
    python src/scrape_reviews.py --cap 500       # quick test
    python src/scrape_reviews.py --only com.healthifyme.basic

Writes one JSONL per app to data/raw/<app_id>.jsonl (resumable: an app whose file
already has >= cap rows is skipped). Also writes data/raw/app_meta.json with the
Play Store listing (score, ratings, installs, current version) at scrape time.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from google_play_scraper import Sort, app as play_app, reviews

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apps import APPS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
BATCH = 200          # Play Store page size
SLEEP = 0.8          # polite pause between pages


def scrape_app(app_id: str, cap: int) -> int:
    out = RAW / f"{app_id}.jsonl"
    have = sum(1 for _ in out.open(encoding="utf-8")) if out.exists() else 0
    if have >= cap:
        print(f"  skip {app_id}: already {have} rows")
        return have
    seen = set()
    if out.exists():
        for line in out.open(encoding="utf-8"):
            seen.add(json.loads(line)["reviewId"])
    token = None
    total = have
    with out.open("a", encoding="utf-8") as fh:
        while total < cap:
            try:
                batch, token = reviews(app_id, lang="en", country="in",
                                       sort=Sort.NEWEST, count=BATCH,
                                       continuation_token=token)
            except Exception as e:  # network hiccup: back off and retry same token
                print(f"  retry {app_id}: {e}")
                time.sleep(5)
                continue
            if not batch:
                break
            for r in batch:
                if r["reviewId"] in seen:
                    continue
                seen.add(r["reviewId"])
                row = {
                    "app_id": app_id,
                    "reviewId": r["reviewId"],
                    "userName": r.get("userName"),
                    "score": r["score"],
                    "content": r.get("content") or "",
                    "thumbsUpCount": r.get("thumbsUpCount", 0),
                    "appVersion": r.get("appVersion") or r.get("reviewCreatedVersion"),
                    "at": r["at"].isoformat(),
                    "replyContent": r.get("replyContent"),
                    "repliedAt": r["repliedAt"].isoformat() if r.get("repliedAt") else None,
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                total += 1
            fh.flush()
            print(f"  {app_id}: {total}", flush=True)
            if token is None:
                break
            time.sleep(SLEEP)
    return total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, help="override per-app cap")
    ap.add_argument("--only", help="single app_id")
    args = ap.parse_args()

    meta = {}
    grand = 0
    for app_id, name, segment, cap in APPS:
        if args.only and app_id != args.only:
            continue
        cap = args.cap or cap
        print(f"== {name} ({app_id}) cap={cap}")
        try:
            a = play_app(app_id, lang="en", country="in")
            meta[app_id] = {"name": name, "segment": segment, "title": a["title"],
                            "score": a["score"], "ratings": a["ratings"],
                            "reviews_with_text": a["reviews"], "installs": a["installs"],
                            "version": a.get("version"), "developer": a.get("developer"),
                            "scraped_at": time.strftime("%Y-%m-%d")}
        except Exception as e:
            print(f"  meta failed: {e}")
        grand += scrape_app(app_id, cap)
    if meta:
        existing = {}
        mp = RAW / "app_meta.json"
        if mp.exists():
            existing = json.loads(mp.read_text(encoding="utf-8"))
        existing.update(meta)
        mp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. {grand} reviews on disk across {len(APPS)} apps.")


if __name__ == "__main__":
    main()
