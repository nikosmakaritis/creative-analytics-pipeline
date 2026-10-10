import math

import numpy as np
import pandas as pd

from creative_analytics import config as cfg

VIEWER_SD = 0.06
NOISE_SD = 0.05
RATING_SD = 0.9


def weighted_choice(rng: np.random.Generator, options: dict[str, float], size: int) -> np.ndarray:
    return rng.choice(list(options), size=size, p=list(options.values()))


def generate_viewers(rng: np.random.Generator) -> pd.DataFrame:
    n = cfg.N_VIEWERS
    return pd.DataFrame(
        {
            "viewer_id": [f"v{i:04d}" for i in range(1, n + 1)],
            "age_group": weighted_choice(rng, cfg.AGE_GROUPS, n),
            "gender": weighted_choice(rng, cfg.GENDERS, n),
            "region": weighted_choice(rng, cfg.REGIONS, n),
        }
    )


def assign_sessions(rng: np.random.Generator, viewers: pd.DataFrame, creative_ids: list[str]) -> pd.DataFrame:
    low, high = cfg.CREATIVES_PER_VIEWER
    rows = []
    for viewer_id in viewers["viewer_id"]:
        shown = rng.choice(len(creative_ids), size=rng.integers(low, high + 1), replace=False)
        rows += [{"viewer_id": viewer_id, "creative_id": creative_ids[i]} for i in sorted(shown)]
    sessions = pd.DataFrame(rows)
    offsets = rng.integers(0, cfg.FIELDWORK_DAYS * 24 * 3600, size=len(sessions))
    sessions["started_at"] = pd.Timestamp(cfg.FIELDWORK_START) + pd.to_timedelta(offsets, unit="s")
    sessions.insert(0, "session_id", [f"s{i:05d}" for i in range(1, len(sessions) + 1)])
    return sessions


def simulate_watch_time(rng: np.random.Generator, n: int, duration: float, completion_rate: float) -> np.ndarray:
    leave_rate = -math.log(completion_rate) / duration
    return np.minimum(rng.exponential(1 / leave_rate, n), duration).round(2)


def simulate_biometrics(
    rng: np.random.Generator, sessions: pd.DataFrame, duration: float, profile: cfg.ResponseProfile
) -> pd.DataFrame:
    n_sessions, n_seconds = len(sessions), math.ceil(duration)
    progress = np.arange(n_seconds) / duration
    viewer_effect = rng.normal(0, VIEWER_SD, (n_sessions, 1))
    attention = profile.attention - profile.attention_decay * progress + viewer_effect
    attention = attention + rng.normal(0, NOISE_SD, (n_sessions, n_seconds))
    engagement = profile.engagement + viewer_effect + rng.normal(0, NOISE_SD, (n_sessions, n_seconds))

    seconds_watched = np.minimum(np.floor(sessions["watch_time_seconds"].to_numpy()).astype(int) + 1, n_seconds)
    session_index, second = np.nonzero(np.arange(n_seconds) < seconds_watched[:, None])
    return pd.DataFrame(
        {
            "session_id": sessions["session_id"].to_numpy()[session_index],
            "second": second,
            "attention_score": np.clip(attention, 0, 1)[session_index, second].round(4),
            "engagement_score": np.clip(engagement, 0, 1)[session_index, second].round(4),
        }
    )


def rating(rng: np.random.Generator, average: float, n: int) -> np.ndarray:
    return np.clip(np.rint(rng.normal(average, RATING_SD, n)), 1, 5).astype(int)


def simulate_surveys(rng: np.random.Generator, sessions: pd.DataFrame, profile: cfg.ResponseProfile) -> pd.DataFrame:
    n = len(sessions)
    return pd.DataFrame(
        {
            "session_id": sessions["session_id"].to_numpy(),
            "brand_recall": rng.random(n) < profile.brand_recall,
            "likability": rating(rng, profile.likability, n),
            "purchase_intent": rating(rng, profile.purchase_intent, n),
            "emotional_impact": rating(rng, profile.emotional_impact, n),
        }
    )


def generate(creatives: pd.DataFrame, seed: int = cfg.RANDOM_SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    viewers = generate_viewers(rng)
    sessions = assign_sessions(rng, viewers, creatives["creative_id"].tolist())

    session_parts, biometric_parts, survey_parts = [], [], []
    for creative in creatives.itertuples():
        profile = cfg.RESPONSE_PROFILES[creative.creative_id]
        part = sessions[sessions["creative_id"] == creative.creative_id].copy()
        part["watch_time_seconds"] = simulate_watch_time(rng, len(part), creative.duration_seconds, profile.completion_rate)
        part["completion_pct"] = (part["watch_time_seconds"] / creative.duration_seconds).round(4)
        part["completed"] = part["watch_time_seconds"] >= creative.duration_seconds
        session_parts.append(part)
        biometric_parts.append(simulate_biometrics(rng, part, creative.duration_seconds, profile))
        survey_parts.append(simulate_surveys(rng, part, profile))

    return {
        "viewers": viewers,
        "viewing_sessions": pd.concat(session_parts).sort_values("session_id", ignore_index=True),
        "biometric_events": pd.concat(biometric_parts).sort_values(["session_id", "second"], ignore_index=True),
        "survey_responses": pd.concat(survey_parts).sort_values("session_id", ignore_index=True),
    }


def main() -> None:
    creatives = pd.read_parquet(cfg.WAREHOUSE_DIR / "creatives.parquet")
    for name, table in generate(creatives).items():
        table.to_parquet(cfg.WAREHOUSE_DIR / f"{name}.parquet", index=False)
        print(f"{name}: {len(table):,} rows")


if __name__ == "__main__":
    main()
