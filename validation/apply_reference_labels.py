"""
Reference labels for the 300-review validation sample.

Annotator: Claude (Fable 5.1), reading each review one at a time in a separate session pass on
2026-10-02, with taxonomy.md and labelling_guide.md open. This is NOT the batch classifier
(a different model, prompt and process), but it is also not a human. Om is to spot-check at
least 50 rows and overwrite any he disagrees with; disagreements are themselves useful data.

Run: python validation/apply_reference_labels.py   (writes human_label into to_label.csv, row order)
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHEET = HERE / "to_label.csv"

LABELS = """
other_complaint crash content_quality paywall login paywall ux other_complaint paywall paywall
performance crash no_complaint paywall paywall no_complaint no_complaint no_complaint no_complaint no_complaint
paywall paywall paywall paywall paywall crash paywall login food_db paywall
content_quality no_complaint no_complaint content_quality no_complaint food_db no_complaint no_complaint no_complaint no_complaint
crash food_db login food_db other_complaint food_db login paywall paywall login
paywall ux login paywall paywall no_complaint no_complaint no_complaint no_complaint no_complaint
login coach_support login crash login login login content_quality login login
content_quality crash performance performance no_complaint crash no_complaint no_complaint no_complaint no_complaint
food_db ux food_db login ux crash login privacy privacy food_db
ux food_db no_complaint device_sync performance no_complaint no_complaint no_complaint no_complaint no_complaint
coach_support coach_support content_quality content_quality content_quality performance other_complaint coach_support coach_support crash
food_db login no_complaint no_complaint coach_support no_complaint no_complaint no_complaint no_complaint no_complaint
paywall coach_support spam billing coach_support coach_support coach_support paywall crash other_complaint
crash ux ux no_complaint paywall crash no_complaint no_complaint no_complaint no_complaint
login paywall billing paywall paywall privacy paywall ux ux ux
ux paywall billing food_db crash no_complaint no_complaint paywall no_complaint no_complaint
content_quality login billing crash privacy billing paywall paywall ux ux
content_quality crash performance device_sync crash no_complaint ux no_complaint no_complaint no_complaint
login billing ux crash privacy coach_support login ux ux ux
ux ux login paywall crash ux paywall login no_complaint no_complaint
paywall paywall content_quality ux tracking login crash food_db other_complaint login
paywall paywall ux paywall content_quality food_db no_complaint no_complaint no_complaint no_complaint
crash crash crash billing billing billing content_quality billing other_complaint crash
crash crash paywall ux device_sync no_complaint no_complaint no_complaint no_complaint no_complaint
tracking crash other_complaint login crash ux device_sync ux tracking other_complaint
crash ux no_complaint tracking tracking no_complaint device_sync no_complaint no_complaint no_complaint
paywall other_complaint crash paywall ux ux other_complaint ux paywall paywall
paywall performance ux food_db ux ux food_db ux no_complaint localisation
coach_support coach_support other_complaint crash other_complaint coach_support content_quality crash ux coach_support
performance coach_support crash crash performance coach_support no_complaint no_complaint no_complaint no_complaint
""".split()

SEVERITY = {"billing": 3, "login": 3, "privacy": 3, "crash": 2, "device_sync": 2, "tracking": 2, "food_db": 2,
            "coach_support": 2, "content_quality": 2}


def main() -> None:
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8")))
    assert len(rows) == len(LABELS) == 300, (len(rows), len(LABELS))
    for r, lab in zip(rows, LABELS):
        if not (r.get("human_label") or "").strip():          # never overwrite a hand edit
            r["human_label"] = lab
            r["human_severity"] = SEVERITY.get(lab, 1)
            r["human_notes"] = "claude-reference"
    with SHEET.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"applied {len(LABELS)} reference labels to {SHEET}")


if __name__ == "__main__":
    main()
