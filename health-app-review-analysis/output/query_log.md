# Query log (classifier = llm)

## 01_complaint_mix_by_app (214 rows)

```sql
-- Complaint mix per app: what share of each app's complaints is each label.
-- llm is substituted by run_queries.py (llm or keyword).
WITH labelled AS (
    SELECT r.review_id, a.name AS app, a.segment, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = 'llm'
    JOIN apps a USING (app_id)
),
per_app AS (
    SELECT app, segment,
           COUNT(*)                                       AS n_reviews,
           SUM(CASE WHEN is_complaint THEN 1 ELSE 0 END)  AS n_complaints,
           ROUND(AVG(score), 2)                           AS avg_rating
    FROM labelled GROUP BY app, segment
),
mix AS (
    SELECT app, label, COUNT(*) AS n
    FROM labelled WHERE is_complaint
    GROUP BY app, label
)
SELECT m.app, p.segment, p.n_reviews, p.n_complaints,
       ROUND(100.0 * p.n_complaints / p.n_reviews, 1)      AS complaint_rate_pct,
       p.avg_rating,
       m.label, m.n,
       ROUND(100.0 * m.n / p.n_complaints, 1)              AS pct_of_complaints,
       RANK() OVER (PARTITION BY m.app ORDER BY m.n DESC)   AS rank_in_app
FROM mix m JOIN per_app p USING (app)
ORDER BY m.app, m.n DESC;
```

## 02_category_wide (15 rows)

```sql
-- Which complaints are category-wide (every app has them) vs app-specific?
-- For each label: average share across apps, spread, and how many apps have it in their top 3.
WITH labelled AS (
    SELECT a.name AS app, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = 'llm'
    JOIN apps a USING (app_id)
),
per_app_share AS (
    SELECT app, label,
           COUNT(*) AS n,
           100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY app) AS share_pct,
           RANK() OVER (PARTITION BY app ORDER BY COUNT(*) DESC)  AS rnk
    FROM labelled WHERE is_complaint
    GROUP BY app, label
)
SELECT label,
       SUM(n)                                        AS total_complaints,
       ROUND(100.0 * SUM(n) / SUM(SUM(n)) OVER (), 1) AS pct_of_all_complaints,
       COUNT(DISTINCT app)                           AS apps_with_it,
       SUM(CASE WHEN rnk <= 3 THEN 1 ELSE 0 END)     AS apps_where_top3,
       ROUND(AVG(share_pct), 1)                      AS avg_share_pct,
       ROUND(MIN(share_pct), 1)                      AS min_share_pct,
       ROUND(MAX(share_pct), 1)                      AS max_share_pct,
       ROUND(STDDEV_SAMP(share_pct), 1)              AS stddev_share_pct,
       arg_max(app, share_pct)                       AS worst_app
FROM per_app_share
GROUP BY label
ORDER BY total_complaints DESC;
```

## 03_before_after_release (49 rows)

```sql
-- Did a release change the complaint mix? Release proxy = first review seen on a version
-- (Play Store does not expose release dates). Compare the 30 days before first_seen (any version)
-- with the 30 days after (reviews on that version only). Versions with < 50 post-release reviews skipped.
WITH labelled AS (
    SELECT r.review_id, r.app_id, r.app_version, r.reviewed_at, r.score, l.label, l.is_complaint, l.mentions_update
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = 'llm'
),
rel AS (
    SELECT app_id, app_version, first_seen FROM releases WHERE n_reviews >= 50
),
after AS (
    SELECT rel.app_id, rel.app_version, rel.first_seen,
           COUNT(*) AS n_after,
           ROUND(AVG(score), 2) AS rating_after,
           ROUND(100.0 * AVG(CASE WHEN is_complaint THEN 1 ELSE 0 END), 1) AS complaint_pct_after,
           ROUND(100.0 * AVG(CASE WHEN label = 'crash' THEN 1 ELSE 0 END), 1) AS crash_pct_after,
           ROUND(100.0 * AVG(CASE WHEN label = 'login' THEN 1 ELSE 0 END), 1) AS login_pct_after,
           ROUND(100.0 * AVG(CASE WHEN label = 'ux' THEN 1 ELSE 0 END), 1) AS ux_pct_after,
           ROUND(100.0 * AVG(CASE WHEN mentions_update THEN 1 ELSE 0 END), 1) AS mentions_update_pct_after
    FROM rel JOIN labelled lb
      ON lb.app_id = rel.app_id AND lb.app_version = rel.app_version
     AND lb.reviewed_at >= rel.first_seen AND lb.reviewed_at < rel.first_seen + INTERVAL 30 DAY
    GROUP BY rel.app_id, rel.app_version, rel.first_seen
),
before AS (
    SELECT rel.app_id, rel.app_version,
           COUNT(*) AS n_before,
           ROUND(AVG(score), 2) AS rating_before,
           ROUND(100.0 * AVG(CASE WHEN is_complaint THEN 1 ELSE 0 END), 1) AS complaint_pct_before,
           ROUND(100.0 * AVG(CASE WHEN label = 'crash' THEN 1 ELSE 0 END), 1) AS crash_pct_before,
           ROUND(100.0 * AVG(CASE WHEN label = 'login' THEN 1 ELSE 0 END), 1) AS login_pct_before,
           ROUND(100.0 * AVG(CASE WHEN label = 'ux' THEN 1 ELSE 0 END), 1) AS ux_pct_before
    FROM rel JOIN labelled lb
      ON lb.app_id = rel.app_id
     AND lb.reviewed_at < rel.first_seen AND lb.reviewed_at >= rel.first_seen - INTERVAL 30 DAY
    GROUP BY rel.app_id, rel.app_version
)
SELECT a.name AS app, af.app_version, CAST(af.first_seen AS DATE) AS release_proxy_date,
       b.n_before, af.n_after,
       b.rating_before, af.rating_after, ROUND(af.rating_after - b.rating_before, 2) AS rating_delta,
       b.complaint_pct_before, af.complaint_pct_after, ROUND(af.complaint_pct_after - b.complaint_pct_before, 1) AS complaint_delta_pp,
       b.crash_pct_before, af.crash_pct_after, ROUND(af.crash_pct_after - b.crash_pct_before, 1) AS crash_delta_pp,
       b.login_pct_before, af.login_pct_after,
       b.ux_pct_before, af.ux_pct_after,
       af.mentions_update_pct_after
FROM after af JOIN before b USING (app_id, app_version) JOIN apps a USING (app_id)
WHERE af.n_after >= 50 AND b.n_before >= 50
ORDER BY complaint_delta_pp DESC;
```

## 04_rating_and_upvotes_by_label (16 rows)

```sql
-- Which complaints hurt the rating most, and which ones other users upvote (resonance).
-- thumbs_up is the Play Store "helpful" count: a complaint with high median upvotes is one many users share.
WITH labelled AS (
    SELECT r.score, r.thumbs_up, r.content_len, l.label, l.severity, l.mentions_update
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = 'llm'
)
SELECT label,
       COUNT(*)                                                     AS n,
       ROUND(AVG(score), 2)                                         AS avg_rating,
       ROUND(100.0 * AVG(CASE WHEN score = 1 THEN 1 ELSE 0 END), 1) AS pct_one_star,
       ROUND(AVG(severity), 2)                                      AS avg_severity,
       ROUND(AVG(thumbs_up), 2)                                     AS avg_thumbs_up,
       SUM(thumbs_up)                                               AS total_thumbs_up,
       ROUND(100.0 * SUM(thumbs_up) / SUM(SUM(thumbs_up)) OVER (), 1) AS pct_of_all_thumbs_up,
       ROUND(100.0 * AVG(CASE WHEN mentions_update THEN 1 ELSE 0 END), 1) AS pct_mentions_update,
       ROUND(AVG(content_len))                                      AS avg_chars
FROM labelled
GROUP BY label
ORDER BY n DESC;
```

## 05_monthly_trend (126 rows)

```sql
-- Monthly trend per app: volume, rating, complaint rate and the two most actionable buckets.
WITH labelled AS (
    SELECT a.name AS app, r.year_month, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = 'llm'
    JOIN apps a USING (app_id)
)
SELECT app, year_month,
       COUNT(*) AS n,
       ROUND(AVG(score), 2) AS avg_rating,
       ROUND(100.0 * AVG(CASE WHEN is_complaint THEN 1 ELSE 0 END), 1)       AS complaint_pct,
       ROUND(100.0 * AVG(CASE WHEN label = 'billing' THEN 1 ELSE 0 END), 1)  AS billing_pct,
       ROUND(100.0 * AVG(CASE WHEN label = 'crash' THEN 1 ELSE 0 END), 1)    AS crash_pct,
       ROUND(100.0 * AVG(CASE WHEN label = 'food_db' THEN 1 ELSE 0 END), 1)  AS food_db_pct,
       ROUND(100.0 * AVG(CASE WHEN label = 'paywall' THEN 1 ELSE 0 END), 1)  AS paywall_pct
FROM labelled
GROUP BY app, year_month
HAVING COUNT(*) >= 30
ORDER BY app, year_month;
```

## 06_india_vs_global (15 rows)

```sql
-- Global trackers vs India-built coaching apps: do Indian users complain about different things?
-- segment comes from src/apps.py (india_coach, india_fitness, global_tracker, global_coach, ai_photo, fasting, platform).
WITH labelled AS (
    SELECT CASE WHEN a.segment IN ('india_coach', 'india_fitness') THEN 'india_built'
                WHEN a.segment IN ('global_tracker', 'global_coach', 'ai_photo', 'fasting') THEN 'global'
                ELSE 'platform' END AS origin,
           a.name AS app, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = 'llm'
    JOIN apps a USING (app_id)
),
per_origin AS (
    SELECT origin, label,
           COUNT(*) AS n,
           100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY origin) AS share_pct
    FROM labelled WHERE is_complaint
    GROUP BY origin, label
)
SELECT label,
       ROUND(MAX(CASE WHEN origin = 'india_built' THEN share_pct END), 1) AS india_built_pct,
       ROUND(MAX(CASE WHEN origin = 'global' THEN share_pct END), 1)      AS global_pct,
       ROUND(MAX(CASE WHEN origin = 'platform' THEN share_pct END), 1)    AS platform_pct,
       ROUND(COALESCE(MAX(CASE WHEN origin = 'india_built' THEN share_pct END), 0)
             - COALESCE(MAX(CASE WHEN origin = 'global' THEN share_pct END), 0), 1) AS india_minus_global_pp,
       SUM(n) AS n
FROM per_origin
GROUP BY label
ORDER BY ABS(india_minus_global_pp) DESC;
```

## 07_language_split (30 rows)

```sql
-- Hinglish / Hindi reviewers vs English reviewers: same complaints, or a different user?
-- lang_hint is a heuristic from build_db.py (Devanagari script -> hi, 2+ Hinglish function words -> hinglish).
WITH labelled AS (
    SELECT r.lang_hint, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = 'llm'
),
tot AS (
    SELECT lang_hint, COUNT(*) AS n_reviews, ROUND(AVG(score), 2) AS avg_rating,
           ROUND(100.0 * AVG(CASE WHEN is_complaint THEN 1 ELSE 0 END), 1) AS complaint_pct
    FROM labelled GROUP BY lang_hint
),
mix AS (
    SELECT lang_hint, label, COUNT(*) AS n,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY lang_hint), 1) AS share_of_complaints_pct
    FROM labelled WHERE is_complaint GROUP BY lang_hint, label
)
SELECT m.lang_hint, t.n_reviews, t.avg_rating, t.complaint_pct, m.label, m.n, m.share_of_complaints_pct
FROM mix m JOIN tot t USING (lang_hint)
ORDER BY m.lang_hint, m.n DESC;
```
