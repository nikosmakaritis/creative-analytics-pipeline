SELECT
    creative_id,
    count(*)                                              AS seconds,
    sum(is_scene_cut::INT)                                AS seconds_with_a_cut,
    round(sum(is_scene_cut::INT) * 60.0 / count(*), 1)    AS cuts_per_minute,
    round(avg(motion_score), 4)                           AS avg_motion,
    round(avg(audio_loudness_db), 1)                      AS avg_loudness_db
FROM raw.creative_timeline
GROUP BY creative_id
ORDER BY cuts_per_minute DESC;

SELECT
    creative_id,
    count(*)                              AS n_sessions,
    round(avg(completed::INT), 2)         AS completion_rate,
    round(avg(avg_attention), 3)          AS avg_attention,
    round(avg(brand_recall::INT), 2)      AS brand_recall_rate,
    round(avg(likability), 2)             AS avg_likability,
    round(avg(purchase_intent), 2)        AS avg_purchase_intent,
    round(avg(emotional_impact), 2)       AS avg_emotional_impact
FROM analytics.session_facts
GROUP BY creative_id
ORDER BY avg_attention DESC;

SELECT creative_id, progress_bin_start, avg_attention, pct_viewers_remaining
FROM analytics.attention_by_progress
ORDER BY creative_id, progress_bin_start;

SELECT creative_id, age_group, count(*) AS n_sessions, round(avg(avg_attention), 3) AS avg_attention
FROM analytics.session_facts
GROUP BY ALL
ORDER BY creative_id, age_group;

SELECT t.second, t.is_scene_cut, t.audio_loudness_db, round(avg(e.attention_score), 3) AS avg_attention
FROM raw.creative_timeline t
JOIN raw.viewing_sessions s USING (creative_id)
JOIN raw.biometric_events e ON e.session_id = s.session_id AND e.second = t.second
WHERE t.creative_id = 'elf_caro_lip_oil'
GROUP BY ALL
ORDER BY t.second;
