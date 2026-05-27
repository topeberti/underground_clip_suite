from pathlib import Path

import cv2
import numpy as np


def _motion_score(cap: cv2.VideoCapture, total_frames: int, sample_pairs: int = 10) -> float:
    step = max(1, total_frames // sample_pairs)
    indices = list(range(0, total_frames - step, step))
    if not indices:
        return 0.0

    magnitudes = []
    for i in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok1, f1 = cap.read()
        cap.set(cv2.CAP_PROP_POS_FRAMES, i + step)
        ok2, f2 = cap.read()
        if not ok1 or not ok2:
            continue
        g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(g1, g2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean()
        magnitudes.append(mag)

    if not magnitudes:
        return 0.0
    return min(float(np.mean(magnitudes)) / 25.0, 1.0)


def _brightness_variance_score(cap: cv2.VideoCapture, total_frames: int, n_frames: int = 10) -> float:
    if total_frames == 0:
        return 0.5

    indices = [int(i * total_frames / n_frames) for i in range(n_frames)]
    means = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        means.append(float(np.mean(frame)))

    if len(means) < 2:
        return 0.5
    return min(float(np.std(means)) / 60.0, 1.0)


def score_clip(path: Path) -> float:
    cap = cv2.VideoCapture(str(path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    try:
        motion = _motion_score(cap, total_frames)
        brightness = _brightness_variance_score(cap, total_frames)
    finally:
        cap.release()
    return min(0.7 * motion + 0.3 * brightness, 1.0)
