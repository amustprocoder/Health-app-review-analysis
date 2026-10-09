-- Monthly trend per app: volume, rating, complaint rate and the two most actionable buckets.
WITH labelled AS (
    SELECT a.name AS app, r.year_month, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = '{classifier}'
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
