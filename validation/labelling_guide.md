# Hand-labelling guide (300 reviews, ~2 hours)

File: `validation/to_label.csv`. Fill `human_label` with one code from `taxonomy.md`.
Optionally `human_severity` (1-3) and `human_notes`.

**This step is yours, not the model's.** The whole point is an independent judgement to
score the classifier against. Do not look at the classifier's label while labelling
(the sheet deliberately does not include it).

## Rules of thumb

1. **First complaint wins.** If the review opens with "app keeps crashing" and later says
   "and support never replied", label `crash`.
2. **Rating is context, not the label.** A 1-star review that only says "worst app" is
   `other_complaint`. A 5-star review that says "love it but barcode scan never works" is
   `food_db` (a complaint inside praise is still a complaint).
3. **Money vs price.** Money actually taken, refund refused, auto-renewal = `billing`.
   "Too expensive", "everything is premium now" = `paywall`.
4. **Data gone after reinstall** = `login`. **Steps not counting** = `tracking`.
   **Watch not syncing** = `device_sync`.
5. **Indian food missing** = `food_db`. **App not made for India / no Hindi / dollars** =
   `localisation`.
6. **Coach / support quality** = `coach_support` even when the reviewer wants money back;
   if the complaint is only about the money, `billing`.
7. **Unreadable, empty, or pure praise** = `no_complaint`. Feature requests without a
   complaint ("please add dark mode") = `no_complaint`.
8. Hinglish and Hindi reviews follow the same rules. "paise kat gaye" = `billing`;
   "bahut slow hai" = `performance`; "bakwas app" alone = `other_complaint`.

## When done

```bash
python src/classify.py --mode keyword
python src/classify.py --mode llm --only-validation      # needs a key; classifies just these 300
python src/validate.py
```

`output/validation_report.md` gives accuracy, Cohen's kappa and per-label F1 for each
classifier. Kappa above 0.6 is substantial agreement; below 0.4 the taxonomy or the prompt
needs work before the SQL numbers mean anything. Report the number either way.
