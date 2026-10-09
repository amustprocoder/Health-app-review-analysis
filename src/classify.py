"""
Classify every review into the taxonomy (taxonomy.md).

Two classifiers, same output table, so they can be compared on the 300 hand labels:

  --mode llm       model reads 25 reviews per call, returns JSON per review (resumable, checkpointed)
  --mode keyword   deterministic regex baseline, no key needed; runs in seconds

    python src/classify.py --mode keyword
    python src/classify.py --mode llm --limit 500          # test run
    python src/classify.py --mode llm                       # all reviews

Provider: ANTHROPIC_API_KEY -> Claude (claude-opus-5-5 default; set LABEL_DECODER_MODEL=claude-haiku-4-5
for a cheaper bulk run), else GEMINI_API_KEY -> gemini-2.5-flash (free tier, slow).

Writes table `labels` in data/reviews.duckdb:
  review_id, classifier, label, is_complaint, mentions_update, severity, model
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm import model_id, provider, text_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "reviews.duckdb"
TAXONOMY = (ROOT / "taxonomy.md").read_text(encoding="utf-8")

LABELS = ["billing", "paywall", "login", "crash", "performance", "food_db", "tracking", "device_sync",
          "coach_support", "spam", "ux", "content_quality", "privacy", "localisation", "other_complaint", "no_complaint"]

BATCH = 25
SCHEMA = {
    "type": "object",
    "properties": {
        "results": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "label": {"type": "string", "enum": LABELS},
                "mentions_update": {"type": "boolean"},
                "severity": {"type": "integer", "minimum": 1, "maximum": 3},
            },
            "required": ["id", "label", "mentions_update", "severity"], "additionalProperties": False}}},
    "required": ["results"], "additionalProperties": False,
}
SYSTEM = ("You label Play Store reviews of health and nutrition apps in India using a fixed taxonomy. "
          "Reviews may be in English, Hindi or Hinglish. Pick exactly one label per review: the root cause the "
          "reviewer leads with. Praise or neutral text is no_complaint. Severity: 1 annoyance, 2 feature unusable, "
          "3 money lost / data lost / unsafe advice. mentions_update is true only when the reviewer links the "
          "problem to an update or version.\n\nTaxonomy:\n" + TAXONOMY)

# ------------------------------------------------------------------ keyword baseline
KEYWORDS: list[tuple[str, str]] = [
    ("billing", r"\b(refund|charged|charge|deduct|auto[\s-]*renew|renew|money\s*(?:back|gone|cut|deducted)|paisa|paise|"
                r"subscription\s*(?:cancel|charged|renew)|trial|unsubscribe|payment\s*(?:fail|issue|problem)|scam|fraud|cheat|loot)\b"),
    ("paywall", r"\b(premium|paywall|pro\s*version|everything\s*is\s*paid|locked|unlock|ads?|advertis|upgrade\s*to|pay\s*to|"
                r"nothing\s*is\s*free|free\s*version|expensive|costly|pricey|price)\b"),
    ("login", r"\b(log\s*in|login|sign\s*in|otp|password|account|verif|data\s*(?:lost|gone|wiped|deleted|erased)|lost\s*(?:all\s*)?(?:my\s*)?data|"
              r"reinstall|new\s*phone|sync(?:ing)?\s*(?:between|across)|restore)\b"),
    ("crash", r"\b(crash|crashing|crashes|freez|hang|hangs|stuck|not\s*(?:opening|open|working|work|loading|load|responding)|"
              r"blank\s*screen|white\s*screen|black\s*screen|bug|bugs|buggy|glitch|error|doesn.?t\s*work|won.?t\s*open|keeps\s*closing|force\s*clos)\b"),
    ("performance", r"\b(slow|lag|laggy|battery|drain|heavy|hogs?|storage|space|loading\s*(?:time|forever)|takes\s*(?:too\s*)?long|data\s*usage)\b"),
    ("food_db", r"\b(calorie|calories|macro|macros|protein\s*(?:count|value)|database|food\s*(?:item|list|database|not\s*(?:found|available|there))|"
                r"indian\s*food|roti|dal|sabzi|paneer|biryani|barcode|scan|scanner|wrong\s*(?:calorie|value|nutrition)|portion|serving|"
                r"photo\s*(?:recognition|scan)|recogni[sz]e|inaccurate|not\s*accurate|incorrect)\b"),
    ("tracking", r"\b(steps?\s*(?:count|counter|not|wrong|missing)|step\s*count|pedometer|workout\s*(?:not|didn)|not\s*(?:tracking|recorded|counting)|"
                 r"heart\s*rate|sleep\s*(?:track|data)|gps|distance|weight\s*(?:not|log))\b"),
    ("device_sync", r"\b(google\s*fit|health\s*connect|fitbit|smart\s*watch|smartwatch|watch|band|wearable|garmin|apple\s*health|"
                    r"mi\s*band|noise|boat|pair|pairing|bluetooth|sync(?:ing)?\s*(?:issue|problem|not|fail|stopped|with))\b"),
    ("coach_support", r"\b(coach|coaches|trainer|dietitian|dietician|nutritionist|support|customer\s*(?:care|service)|help\s*(?:desk|line)|"
                      r"no\s*(?:response|reply)|not\s*responding|ticket|chatbot|bot\s*reply|unresponsive|ignored|no\s*one\s*(?:replies|responds))\b"),
    ("spam", r"\b(spam|call(?:s|ing)?\s*(?:me|again|daily|every)|phone\s*calls?|whatsapp|notification|notifications|marketing|promotional|harass|pester)\b"),
    ("ux", r"\b(ui|ux|interface|design|layout|confusing|cluttered|navigation|redesign|new\s*(?:design|update\s*looks|layout)|"
           r"hard\s*to\s*(?:use|find|navigate)|too\s*many\s*(?:steps|clicks|screens)|font|dark\s*mode|complicated)\b"),
    ("content_quality", r"\b(diet\s*plan|meal\s*plan|plan\s*(?:is|was)\s*(?:generic|same|useless|bad)|generic|advice|recommend|"
                        r"workout\s*(?:plan|too)|unsafe|dangerous|starv|wrong\s*(?:advice|plan|suggestion)|ai\s*(?:coach|is)\s*(?:useless|wrong|dumb))\b"),
    ("privacy", r"\b(privacy|permission|permissions|personal\s*data|data\s*(?:selling|sell|sold|shar)|delete\s*(?:my\s*)?account|"
                r"location\s*(?:access|tracking)|contacts?\s*access|tracking\s*me|spy)\b"),
    ("localisation", r"\b(hindi|tamil|telugu|kannada|marathi|bengali|gujarati|language|regional|indian\s*(?:user|context|version)|"
                     r"not\s*(?:for|made\s*for)\s*india|dollar|usd|\$|kg\s*(?:to|and)\s*lbs|lbs|pounds|miles|imperial|metric|not\s*available\s*in\s*india)\b"),
]
POSITIVE = re.compile(r"\b(good|great|nice|love|awesome|excellent|best|amazing|helpful|superb|wonderful|perfect|fantastic|"
                      r"useful|easy|recommend(?:ed)?|thank|thanks|badhiya|mast|accha|achha|acha|bahut\s*acha|zabardast)\b", re.I)
NEGATIVE = re.compile(r"\b(bad|worst|waste|useless|poor|terrible|horrible|pathetic|bakwas|bekar|bekaar|ghatiya|fraud|scam|"
                      r"not\s*working|doesn.?t\s*work|disappoint|frustrat|annoy|hate|never|uninstall|don.?t\s*(?:buy|download|install|use))\b", re.I)
UPDATE = re.compile(r"\b(update|updated|new\s*version|latest\s*version|after\s*(?:the\s*)?(?:update|upgrade)|since\s*(?:the\s*)?update|version)\b", re.I)


def keyword_classify(text: str, score: int) -> dict:
    t = text.lower()
    hits = []
    for label, pat in KEYWORDS:
        m = re.search(pat, t)
        if m:
            hits.append((m.start(), label))
    negative = score <= 3 or NEGATIVE.search(t) is not None
    positive = POSITIVE.search(t) is not None and NEGATIVE.search(t) is None
    if hits and (negative or score <= 3):
        label = sorted(hits)[0][1]              # earliest-mentioned topic wins (mirrors "first sentence wins")
    elif score <= 2 and not positive:
        label = "other_complaint"
    elif negative and not positive and len(t) > 15:
        label = "other_complaint"
    else:
        label = "no_complaint"
    sev = 1
    if label in ("billing", "login", "privacy"):
        sev = 3
    elif label in ("crash", "device_sync", "tracking", "food_db", "coach_support"):
        sev = 2
    if label == "no_complaint":
        sev = 1
    return {"label": label, "is_complaint": label != "no_complaint", "mentions_update": bool(UPDATE.search(t)), "severity": sev}


# ------------------------------------------------------------------ LLM classifier
def llm_classify_batch(batch: list[tuple[str, int, str]]) -> dict[str, dict]:
    lines = []
    for i, (_rid, score, text) in enumerate(batch):
        text = text.replace("\n", " ")[:600]
        lines.append(f"[{i}] (rating {score}/5) {text}")
    prompt = ("Label each review. Return results for every id.\n\n" + "\n".join(lines))
    data = text_json(prompt, SCHEMA, system=SYSTEM, max_tokens=4000)
    out = {}
    for r in data.get("results", []):
        idx = r.get("id")
        if isinstance(idx, int) and 0 <= idx < len(batch) and r.get("label") in LABELS:
            out[batch[idx][0]] = {"label": r["label"], "is_complaint": r["label"] != "no_complaint",
                                  "mentions_update": bool(r.get("mentions_update")), "severity": int(r.get("severity") or 1)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["llm", "keyword"], default="keyword")
    ap.add_argument("--limit", type=int, help="max reviews to classify this run")
    ap.add_argument("--only-validation", action="store_true", help="classify only the 300 validation sample")
    args = ap.parse_args()

    con = duckdb.connect(str(DB))
    con.execute("""CREATE TABLE IF NOT EXISTS labels (review_id VARCHAR, classifier VARCHAR, label VARCHAR,
                   is_complaint BOOLEAN, mentions_update BOOLEAN, severity INTEGER, model VARCHAR,
                   PRIMARY KEY (review_id, classifier))""")
    if args.mode == "llm" and provider() is None:
        raise SystemExit("Set ANTHROPIC_API_KEY or GEMINI_API_KEY (free: https://aistudio.google.com/apikey), or use --mode keyword.")
    classifier = "keyword" if args.mode == "keyword" else f"llm"
    model = "regex-v1" if args.mode == "keyword" else model_id(provider())

    where = "content_len >= 3"
    if args.only_validation:
        where += " AND review_id IN (SELECT review_id FROM validation_sample)"
    pending = con.execute(f"""SELECT review_id, score, content FROM reviews
                              WHERE {where} AND review_id NOT IN (SELECT review_id FROM labels WHERE classifier = ?)
                              ORDER BY reviewed_at DESC""", [classifier]).fetchall()
    if args.limit:
        pending = pending[: args.limit]
    print(f"{len(pending)} reviews to classify with {classifier} ({model})")

    if args.mode == "keyword":
        import pandas as pd
        rows = []
        for rid, score, text in pending:
            k = keyword_classify(text, score)
            rows.append([rid, classifier, k["label"], k["is_complaint"], k["mentions_update"], k["severity"], model])
        df = pd.DataFrame(rows, columns=["review_id", "classifier", "label", "is_complaint", "mentions_update", "severity", "model"])
        con.execute("INSERT OR REPLACE INTO labels SELECT * FROM df")   # bulk insert; executemany is ~100x slower in DuckDB
        con.commit()
    else:
        t0 = time.time()
        for i in range(0, len(pending), BATCH):
            batch = pending[i: i + BATCH]
            try:
                res = llm_classify_batch(batch)
            except Exception as e:
                print(f"  batch {i // BATCH} failed: {e}; sleeping 20s")
                time.sleep(20)
                continue
            rows = [[rid, classifier, r["label"], r["is_complaint"], r["mentions_update"], r["severity"], model]
                    for rid, r in res.items()]
            con.executemany("INSERT OR REPLACE INTO labels VALUES (?,?,?,?,?,?,?)", rows)
            con.commit()
            done = i + len(batch)
            rate = done / max(1, time.time() - t0)
            print(f"  {done}/{len(pending)}  ({len(rows)} labelled, {rate * 60:.0f}/min, ETA {(len(pending) - done) / max(rate, 1e-6) / 60:.0f} min)", flush=True)
    dist = con.execute("SELECT label, COUNT(*) FROM labels WHERE classifier = ? GROUP BY 1 ORDER BY 2 DESC", [classifier]).fetchall()
    print("label distribution:", dist)
    con.close()


if __name__ == "__main__":
    main()
