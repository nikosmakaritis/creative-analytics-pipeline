CREATE OR REPLACE VIEW analytics.attention_by_progress AS
WITH events AS (
    SELECT
        s.creative_id,
        e.session_id,
        least(floor(e.second / c.duration_seconds * 10), 9)::INT * 10 AS progress_bin_start,
        e.attention_score,
        e.engagement_score
    FROM raw.biometric_events e
    JOIN raw.viewing_sessions s USING (session_id)
    JOIN raw.creatives c USING (creative_id)
),
sessions AS (
    SELECT creative_id, count(*) AS n_sessions
    FROM raw.viewing_sessions
    GROUP BY creative_id
)
SELECT
    creative_id,
    progress_bin_start,
    progress_bin_start + 10                                  AS progress_bin_end,
    round(avg(attention_score), 4)                           AS avg_attention,
    round(avg(engagement_score), 4)                          AS avg_engagement,
    count(DISTINCT session_id)                               AS n_viewers_remaining,
    round(count(DISTINCT session_id) / any_value(n_sessions), 3) AS pct_viewers_remaining
FROM events
JOIN sessions USING (creative_id)
GROUP BY creative_id, progress_bin_start;
