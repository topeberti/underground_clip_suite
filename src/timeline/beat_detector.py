from pathlib import Path

import numpy as np
import librosa


def analyze(path: Path) -> dict:
    y, sr = librosa.load(str(path), sr=None)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    duration_sec = float(len(y) / sr)
    return {"bpm": bpm, "beat_times": beat_times, "duration_sec": duration_sec}
