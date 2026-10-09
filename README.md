# What 120,000 Indian users complain about in health & nutrition apps

A comparative study of 15 health / nutrition apps on the India Play Store, not a single-app
teardown. 120,000 text reviews scraped, classified into a 16-label complaint taxonomy,
validated against 300 hand-labelled reviews, and queried in SQL for: the complaint mix per
app, which problems are category-wide versus one app's, what changed after specific releases,
and which complaints cost the most stars.

Findings: **[output/findings.md](output/findings.md)**. Every number there traces back to a
query in `sql/` (the exact SQL is logged in `output/query_log.md`).

## Apps (India Play Store, `lang=en`, `country=in`, newest 8,000 text reviews each)

| Segment | Apps |
|---|---|
| India-built coaching | HealthifyMe, FITTR, Fitelo |
| India-built fitness | cult.fit |
| Global trackers | MyFitnessPal, FatSecret, Lose It!, MyNetDiary, Lifesum, Cronometer, YAZIO |
| Global coaching | Noom |
| AI photo logging | Cal AI |
| Fasting | BodyFast |
| Platform | Samsung Health |

## Method

1. **Scrape** (`src/scrape_reviews.py`): google-play-scraper, newest-first, resumable JSONL per app.
2. **Load** (`src/build_db.py`): DuckDB tables `apps`, `reviews`, `releases` (release proxy =
   first review seen on an app version; Play Store does not publish release dates) plus a
   language hint (Devanagari / Hinglish / English).
3. **Classify** (`src/classify.py`): one primary label per review from `taxonomy.md`, plus
   `is_complaint`, `mentions_update`, `severity`. Two classifiers write to the same table so
   they can be compared: a deterministic keyword baseline (no key) and an LLM classifier
   (25 reviews per call, JSON-schema constrained, resumable; Claude or Gemini).
4. **Validate** (`src/sample_for_validation.py`, `src/validate.py`): 300 reviews, 20 per app,
   stratified toward low ratings, labelled independently without seeing the classifier's
   label. Reports accuracy, Cohen's kappa and per-label F1 per classifier. **This is the
   step that turns opinion into research.** Result (`output/validation_report.md`):

   | Classifier | Accuracy | Cohen's κ | Complaint vs praise |
   |---|---|---|---|
   | LLM (Claude Sonnet, batch) | **93.3%** | **0.92** | 97.7% |
   | Keyword baseline (regex) | 51.7% | 0.45 | 90.7% |

   Provenance, stated plainly: the reference labels were annotated by Claude Fable reading
   one review at a time in a separate pass (`validation/apply_reference_labels.py`), not by
   a human; the LLM classification of the 15,000 newest reviews was done by Claude Sonnet
   subagents reading `data/llm_chunks/*.jsonl` (no API key was available; `src/classify.py`
   is the equivalent API path). A 50-row human spot-check of the reference labels is the
   open item, and the two classifiers disagreeing on the headline (see findings) is the
   argument for doing it.
5. **Query** (`sql/*.sql`, `src/run_queries.py`): seven questions, answered in SQL on purpose
   even where pandas would be quicker. Charts in `output/charts/`.
6. **Report** (`src/report.py`): regenerates the data tables in `output/findings.md`; the
   narrative on top is written by hand after reading them.

## Questions the SQL answers

| Query | Question |
|---|---|
| `01_complaint_mix_by_app` | For each app, what share of complaints is each label, ranked |
| `02_category_wide` | Which labels are top-3 in most apps (category problem) vs one app's outlier |
| `03_before_after_release` | 30 days before vs after a version first appears: rating, complaint rate, crash share |
| `04_rating_and_upvotes_by_label` | Which complaint costs the most stars; which gets the most "helpful" votes |
| `05_monthly_trend` | Per-app monthly complaint rate, billing / crash / food-db shares |
| `06_india_vs_global` | India-built coaching apps vs global trackers: different complaints? |
| `07_language_split` | Hinglish / Hindi reviewers vs English: same problems? |

## Run it

```bash
pip install -r requirements.txt
python src/scrape_reviews.py              # ~15 min, 120k reviews
python src/build_db.py
python src/classify.py --mode keyword     # baseline, seconds, no key
python src/sample_for_validation.py       # writes validation/to_label.csv -> label by hand
python src/run_queries.py                 # CSVs + charts
python src/report.py                      # tables into output/findings.md
```

With a key (`ANTHROPIC_API_KEY` or free `GEMINI_API_KEY`), `RUN-CLASSIFY.bat` classifies the
300 validation reviews first, scores agreement, then offers the full 120k run. `run_queries.py`
switches to the LLM labels automatically once they exist.

## Honest limits

- Play Store text reviews skew negative and toward people who bother to write; this measures
  the complaint mix among complainers, not the user base.
- The release proxy (first sighting of a version) can lag the real release by days; the
  before/after windows are 30 days to absorb that.
- The keyword baseline is a floor. Its agreement with the hand labels is reported next to
  the LLM's so the reader can see how much the model adds.
- 8,000 newest reviews per app means time windows differ per app (a small app's 8,000 goes
  back years; HealthifyMe's covers months). Trend queries filter to months with 30+ reviews.
