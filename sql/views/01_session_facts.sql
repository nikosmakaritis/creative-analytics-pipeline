CREATE OR REPLACE VIEW analytics.session_facts AS
WITH biometrics AS (
    SELECT
        session_id,
        avg(attention_score)  AS avg_attention,
        avg(engagement_score) AS avg_engagement
    FROM raw.biometric_events
    GROUP BY session_id
)
SELECT
    s.session_id,
    s.viewer_id,
    s.creative_id,
    c.creative_name,
    c.brand,
    c.creative_category,
    c.orientation,
    c.duration_seconds,
    v.age_group,
    v.gender,
    v.region,
    s.started_at,
    s.watch_time_seconds,
    s.completion_pct,
    s.completed,
    b.avg_attention,
    b.avg_engagement,
    r.brand_recall,
    r.likability,
    r.purchase_intent,
    r.emotional_impact
FROM raw.viewing_sessions s
JOIN raw.creatives c USING (creative_id)
JOIN raw.viewers v USING (viewer_id)
LEFT JOIN biometrics b USING (session_id)
LEFT JOIN raw.survey_responses r USING (session_id);
