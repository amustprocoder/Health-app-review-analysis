-- Which complaints hurt the rating most, and which ones other users upvote (resonance).
-- thumbs_up is the Play Store "helpful" count: a complaint with high median upvotes is one many users share.
WITH labelled AS (
    SELECT r.score, r.thumbs_up, r.content_len, l.label, l.severity, l.mentions_update
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = '{classifier}'
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
