import math
from pathlib import Path

import av
import numpy as np
import pandas as pd

from creative_analytics.config import CREATIVES, CREATIVES_DIR, WAREHOUSE_DIR, Creative

FRAME_WIDTH = 160
CUT_MIN_CHANGE = 0.10
CUT_LOCAL_RATIO = 3
CUT_WINDOW_FRAMES = 25
AUDIO_RATE = 16_000
SILENCE_DB = -50.0
LOUDNESS_FLOOR_DB = -100.0


def read_metadata(creative: Creative, path: Path) -> dict:
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        width, height = video.width, video.height
        return {
            "creative_id": creative.creative_id,
            "creative_name": creative.creative_name,
            "filename": creative.filename,
            "brand": creative.brand,
            "creative_category": creative.creative_category,
            "duration_seconds": round(container.duration / av.time_base, 2),
            "width": width,
            "height": height,
            "fps": round(float(video.average_rate), 2),
            "orientation": "landscape" if width > height else "vertical" if height > width else "square",
            "has_audio": len(container.streams.audio) > 0,
            "file_size_bytes": path.stat().st_size,
        }


def video_features(path: Path) -> pd.DataFrame:
    rows = []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        fps = float(stream.average_rate)
        frame_height = round(FRAME_WIDTH * stream.height / stream.width / 2) * 2
        previous = None
        for frame in container.decode(stream):
            if frame.pts is None:
                continue
            luma = frame.reformat(width=FRAME_WIDTH, height=frame_height, format="gray").to_ndarray()
            luma = luma.astype(np.float32) / 255.0
            change = float(np.abs(luma - previous).mean()) if previous is not None else 0.0
            rows.append(
                {"second": int(frame.pts * stream.time_base), "brightness": float(luma.mean()), "change": change}
            )
            previous = luma

    frames = pd.DataFrame(rows)
    local_change = frames["change"].rolling(CUT_WINDOW_FRAMES, center=True, min_periods=1).median()
    frames["is_cut"] = (frames["change"] > CUT_MIN_CHANGE) & (frames["change"] > CUT_LOCAL_RATIO * local_change)
    frames["motion"] = frames["change"].where(~frames["is_cut"]) * fps / 25
    per_second = frames.groupby("second").agg(
        brightness=("brightness", "mean"),
        motion_score=("motion", "mean"),
        is_scene_cut=("is_cut", "any"),
    )
    per_second["motion_score"] = per_second["motion_score"].fillna(0.0)
    return per_second


def audio_features(path: Path) -> pd.DataFrame:
    with av.open(str(path)) as container:
        if not container.streams.audio:
            return pd.DataFrame(columns=["audio_loudness_db"], index=pd.Index([], name="second"))
        resampler = av.AudioResampler(format="flt", layout="mono", rate=AUDIO_RATE)
        chunks = [
            resampled.to_ndarray().ravel()
            for frame in container.decode(audio=0)
            for resampled in resampler.resample(frame)
        ]
    samples = np.concatenate(chunks)
    n_seconds = math.ceil(len(samples) / AUDIO_RATE)
    padded = np.zeros(n_seconds * AUDIO_RATE, dtype=np.float32)
    padded[: len(samples)] = samples
    rms = np.sqrt((padded.reshape(n_seconds, AUDIO_RATE) ** 2).mean(axis=1))
    loudness = 20 * np.log10(np.maximum(rms, 10 ** (LOUDNESS_FLOOR_DB / 20)))
    return pd.DataFrame({"audio_loudness_db": loudness}, index=pd.RangeIndex(n_seconds, name="second"))


def build_timeline(creative_id: str, path: Path, duration_seconds: float) -> pd.DataFrame:
    seconds = pd.RangeIndex(math.ceil(duration_seconds), name="second")
    timeline = video_features(path).reindex(seconds).join(audio_features(path).reindex(seconds))
    timeline["brightness"] = timeline["brightness"].ffill().bfill()
    timeline["motion_score"] = timeline["motion_score"].fillna(0.0)
    timeline["is_scene_cut"] = timeline["is_scene_cut"].fillna(False).astype(bool)
    timeline["audio_loudness_db"] = timeline["audio_loudness_db"].fillna(LOUDNESS_FLOOR_DB).astype("float64")
    timeline["is_silent"] = timeline["audio_loudness_db"] < SILENCE_DB
    timeline = timeline.reset_index()
    timeline.insert(0, "creative_id", creative_id)
    timeline.insert(2, "progress_pct", timeline["second"] / duration_seconds * 100)
    return timeline.round({"progress_pct": 2, "brightness": 4, "motion_score": 4, "audio_loudness_db": 2})[
        ["creative_id", "second", "progress_pct", "is_scene_cut", "motion_score", "brightness",
         "audio_loudness_db", "is_silent"]
    ]


def main() -> None:
    missing = [c.filename for c in CREATIVES if not (CREATIVES_DIR / c.filename).exists()]
    if missing:
        raise SystemExit(f"Missing videos in {CREATIVES_DIR}: {missing}")

    metadata, timelines = [], []
    for creative in CREATIVES:
        path = CREATIVES_DIR / creative.filename
        row = read_metadata(creative, path)
        timeline = build_timeline(creative.creative_id, path, row["duration_seconds"])
        metadata.append(row)
        timelines.append(timeline)
        print(f"{creative.creative_id}: {row['duration_seconds']}s, {int(timeline['is_scene_cut'].sum())} scene cuts")

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metadata).to_parquet(WAREHOUSE_DIR / "creatives.parquet", index=False)
    pd.concat(timelines, ignore_index=True).to_parquet(WAREHOUSE_DIR / "creative_timeline.parquet", index=False)


if __name__ == "__main__":
    main()
