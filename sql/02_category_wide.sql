-- Which complaints are category-wide (every app has them) vs app-specific?
-- For each label: average share across apps, spread, and how many apps have it in their top 3.
WITH labelled AS (
    SELECT a.name AS app, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = '{classifier}'
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
