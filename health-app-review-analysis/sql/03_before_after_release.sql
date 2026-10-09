-- Did a release change the complaint mix? Release proxy = first review seen on a version
-- (Play Store does not expose release dates). Compare the 30 days before first_seen (any version)
-- with the 30 days after (reviews on that version only). Versions with < 50 post-release reviews skipped.
WITH labelled AS (
    SELECT r.review_id, r.app_id, r.app_version, r.reviewed_at, r.score, l.label, l.is_complaint, l.mentions_update
    FROM reviews r
    JOIN labels l ON l.review_id = r.review_id AND l.classifier = '{classifier}'
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
