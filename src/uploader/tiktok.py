"""
src/uploader/tiktok.py — TikTok Content Posting API v2 client.

Handles chunked video uploads with status polling.
"""

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from src.uploader.auth import AuthExpiredError, ensure_tiktok_token

API_BASE = "https://open.tiktokapis.com/v2"
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB

PRIVACY_MAP = {
    "public": "PUBLIC_TO_EVERYONE",
    "followers": "MUTUAL_FOLLOW_FRIENDS",
    "private": "SELF_ONLY",
}


@dataclass
class UploadResult:
    file_path: Path
    platform: str
    status: str          # "success" | "failed" | "skipped"
    publish_id: str = ""
    error_code: str = ""
    error_message: str = ""
    timestamp: str = ""


class TikTokUploader:
    def __init__(self, config: dict, config_path: Path):
        self.access_token = ensure_tiktok_token(config, config_path)
        self._headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def upload_video(
        self,
        file_path: Path,
        caption: str,
        privacy: str = "public",
    ) -> UploadResult:
        from datetime import datetime
        ts = datetime.now().isoformat()

        tiktok_privacy = PRIVACY_MAP.get(privacy, "PUBLIC_TO_EVERYONE")
        file_size = file_path.stat().st_size
        total_chunks = math.ceil(file_size / CHUNK_SIZE)

        for attempt in range(3):
            try:
                result = self._do_upload(file_path, caption, tiktok_privacy, file_size, total_chunks)
                result.timestamp = ts
                return result
            except _RetryableError as exc:
                if attempt == 2:
                    return UploadResult(
                        file_path=file_path,
                        platform="tiktok",
                        status="failed",
                        error_code="upload_failed",
                        error_message=str(exc),
                        timestamp=ts,
                    )
                time.sleep(15 * (2 ** attempt))

        # unreachable
        return UploadResult(file_path=file_path, platform="tiktok", status="failed", timestamp=ts)

    def _do_upload(
        self,
        file_path: Path,
        caption: str,
        tiktok_privacy: str,
        file_size: int,
        total_chunks: int,
    ) -> UploadResult:
        from datetime import datetime

        # Step 1: init upload
        init_resp = requests.post(
            f"{API_BASE}/post/publish/video/init/",
            json={
                "post_info": {
                    "title": caption[:150],  # TikTok title limit
                    "privacy_level": tiktok_privacy,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": CHUNK_SIZE,
                    "total_chunk_count": total_chunks,
                },
            },
            headers=self._headers,
            timeout=30,
        )
        self._raise_for_status(init_resp, "init")
        init_data = init_resp.json().get("data", {})
        publish_id = init_data["publish_id"]
        upload_url = init_data["upload_url"]

        # Step 2: chunk upload
        with open(file_path, "rb") as fh:
            for chunk_idx in range(total_chunks):
                chunk = fh.read(CHUNK_SIZE)
                start = chunk_idx * CHUNK_SIZE
                end = start + len(chunk) - 1
                put_resp = requests.put(
                    upload_url,
                    data=chunk,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Content-Length": str(len(chunk)),
                        "Content-Type": "video/mp4",
                    },
                    timeout=120,
                )
                if put_resp.status_code == 429:
                    raise _RetryableError("Rate limited during chunk upload")
                if put_resp.status_code not in (200, 206):
                    raise _RetryableError(
                        f"Chunk {chunk_idx + 1}/{total_chunks} failed: HTTP {put_resp.status_code}"
                    )

        # Step 3: poll publish status
        deadline = time.time() + 120
        while time.time() < deadline:
            time.sleep(10)
            status_resp = requests.post(
                f"{API_BASE}/post/publish/status/fetch/",
                json={"publish_id": publish_id},
                headers=self._headers,
                timeout=30,
            )
            self._raise_for_status(status_resp, "status")
            status = status_resp.json().get("data", {}).get("status", "")
            if status == "PUBLISH_COMPLETE":
                return UploadResult(
                    file_path=file_path,
                    platform="tiktok",
                    status="success",
                    publish_id=publish_id,
                    timestamp=datetime.now().isoformat(),
                )
            if status == "FAILED":
                fail_reason = status_resp.json().get("data", {}).get("fail_reason", "unknown")
                return UploadResult(
                    file_path=file_path,
                    platform="tiktok",
                    status="failed",
                    publish_id=publish_id,
                    error_code="publish_failed",
                    error_message=fail_reason,
                    timestamp=datetime.now().isoformat(),
                )

        return UploadResult(
            file_path=file_path,
            platform="tiktok",
            status="failed",
            publish_id=publish_id,
            error_code="timeout",
            error_message="Timed out waiting for publish status",
            timestamp=datetime.now().isoformat(),
        )

    @staticmethod
    def _raise_for_status(resp: requests.Response, step: str) -> None:
        if resp.status_code == 429:
            raise _RetryableError(f"Rate limited at {step}")
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise RuntimeError(f"TikTok API error at {step} (HTTP {resp.status_code}): {body}")


class _RetryableError(Exception):
    pass
