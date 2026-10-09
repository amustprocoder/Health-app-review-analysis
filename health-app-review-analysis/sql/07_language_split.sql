-- Hinglish / Hindi reviewers vs English reviewers: same complaints, or a different user?
-- lang_hint is a heuristic from build_db.py (Devanagari script -> hi, 2+ Hinglish function words -> hinglish).
WITH labelled AS (
    SELECT r.lang_hint, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = '{classifier}'
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
