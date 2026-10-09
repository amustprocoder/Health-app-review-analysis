-- Complaint mix per app: what share of each app's complaints is each label.
-- {classifier} is substituted by run_queries.py (llm or keyword).
WITH labelled AS (
    SELECT r.review_id, a.name AS app, a.segment, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = '{classifier}'
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
