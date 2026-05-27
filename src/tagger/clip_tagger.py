from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

import open_clip

from src.tagger.constants import CANDIDATE_TAGS

_MODEL_CACHE: dict = {}


def _load_model() -> tuple:
    if _MODEL_CACHE:
        return (
            _MODEL_CACHE["model"],
            _MODEL_CACHE["preprocess"],
            _MODEL_CACHE["tokenizer"],
            _MODEL_CACHE["device"],
        )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    model = model.to(device)
    model.eval()
    _MODEL_CACHE["model"] = model
    _MODEL_CACHE["preprocess"] = preprocess
    _MODEL_CACHE["tokenizer"] = tokenizer
    _MODEL_CACHE["device"] = device
    return model, preprocess, tokenizer, device


def _sample_frames(cap: cv2.VideoCapture, total_frames: int, n: int) -> list:
    indices = [int(i * total_frames / n) for i in range(n)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if ok:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    return frames


def tag_clip(
    path: Path,
    score_threshold: float = 0.2,
    top_n: int = 10,
) -> tuple[list[str], float, float, int | None, int | None]:
    cap = cv2.VideoCapture(str(path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
    duration_sec = total_frames / fps if fps else 0.0

    n = max(4, int(duration_sec / 5))
    raw_frames = _sample_frames(cap, total_frames, n)
    cap.release()

    model, preprocess, tokenizer, device = _load_model()

    if not raw_frames:
        return [], duration_sec, fps, width, height

    image_tensors = torch.stack([preprocess(Image.fromarray(f)) for f in raw_frames]).to(device)
    text_tokens = tokenizer(CANDIDATE_TAGS).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_tensors)
        text_features = model.encode_text(text_tokens)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        similarity = (image_features @ text_features.T).mean(dim=0)

    scores = similarity.cpu().numpy()
    tagged = [
        (CANDIDATE_TAGS[i], float(scores[i]))
        for i in range(len(CANDIDATE_TAGS))
        if scores[i] >= score_threshold
    ]
    tagged.sort(key=lambda x: x[1], reverse=True)
    tags = [t for t, _ in tagged[:top_n]]

    return tags, duration_sec, fps, width, height
