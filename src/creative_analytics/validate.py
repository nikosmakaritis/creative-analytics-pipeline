import sys

import duckdb

from creative_analytics.build_warehouse import ensure_warehouse

CHECKS = {
    "exactly five creatives": "SELECT abs(count(*) - 5) FROM raw.creatives",
    "session ids are unique": """
        SELECT count(*) FROM (SELECT session_id FROM raw.viewing_sessions GROUP BY 1 HAVING count(*) > 1)
    """,
    "one biometric row per session and second": """
        SELECT count(*) FROM (SELECT session_id, second FROM raw.biometric_events GROUP BY ALL HAVING count(*) > 1)
    """,
    "every session has a known viewer and creative": """
        SELECT count(*)
        FROM raw.viewing_sessions s
        LEFT JOIN raw.viewers v USING (viewer_id)
        LEFT JOIN raw.creatives c USING (creative_id)
        WHERE v.viewer_id IS NULL OR c.creative_id IS NULL
    """,
    "every biometric and survey row belongs to a session": """
        SELECT (SELECT count(*) FROM raw.biometric_events ANTI JOIN raw.viewing_sessions USING (session_id))
             + (SELECT count(*) FROM raw.survey_responses ANTI JOIN raw.viewing_sessions USING (session_id))
    """,
    "biometric scores are within 0-1": """
        SELECT count(*) FROM raw.biometric_events
        WHERE attention_score NOT BETWEEN 0 AND 1 OR engagement_score NOT BETWEEN 0 AND 1
    """,
    "survey ratings are within 1-5": """
        SELECT count(*) FROM raw.survey_responses
        WHERE likability NOT BETWEEN 1 AND 5
           OR purchase_intent NOT BETWEEN 1 AND 5
           OR emotional_impact NOT BETWEEN 1 AND 5
    """,
    "no biometrics after the viewer stopped watching": """
        SELECT count(*)
        FROM raw.biometric_events e JOIN raw.viewing_sessions s USING (session_id)
        WHERE e.second > s.watch_time_seconds
    """,
    "the content timeline covers every second of every creative": """
        SELECT count(*)
        FROM (
            SELECT c.creative_id
            FROM raw.creatives c LEFT JOIN raw.creative_timeline t USING (creative_id)
            GROUP BY c.creative_id, c.duration_seconds
            HAVING count(t.second) <> ceil(c.duration_seconds)
        )
    """,
}


def main() -> None:
    failures = 0
    with duckdb.connect(str(ensure_warehouse()), read_only=True) as con:
        for name, sql in CHECKS.items():
            offending = con.execute(sql).fetchone()[0]
            failures += offending > 0
            print(f"{'FAIL' if offending else 'ok  '}  {name}" + (f"  ({offending:,} rows)" if offending else ""))
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
