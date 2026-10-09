-- Global trackers vs India-built coaching apps: do Indian users complain about different things?
-- segment comes from src/apps.py (india_coach, india_fitness, global_tracker, global_coach, ai_photo, fasting, platform).
WITH labelled AS (
    SELECT CASE WHEN a.segment IN ('india_coach', 'india_fitness') THEN 'india_built'
                WHEN a.segment IN ('global_tracker', 'global_coach', 'ai_photo', 'fasting') THEN 'global'
                ELSE 'platform' END AS origin,
           a.name AS app, r.score, l.label, l.is_complaint
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = '{classifier}'
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
