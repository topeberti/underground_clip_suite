"""
src/uploader/instagram.py — Instagram Graph API Reels client.

Requires a publicly accessible video URL (provided by NgrokServer).
Requires a Business or Creator Instagram account linked to a Facebook Page.
"""

import time
from pathlib import Path

import requests

from src.uploader.auth import AuthExpiredError, ensure_instagram_token
from src.uploader.tiktok import UploadResult  # shared dataclass

API_BASE = "https://graph.facebook.com/v22.0"


class InstagramUploader:
    def __init__(self, config: dict, config_path: Path):
        self.access_token = ensure_instagram_token(config, config_path)
        self.ig_user_id = config.get("instagram", {}).get("ig_user_id", "")
        if not self.ig_user_id:
            raise ValueError(
                "Instagram ig_user_id not set in config. "
                "Re-run: python src/main.py setup-upload --platform instagram"
            )

    def upload_reel(
        self,
        file_path: Path,
        caption: str,
        public_url: str,
    ) -> UploadResult:
        from datetime import datetime
        ts = datetime.now().isoformat()

        try:
            container_id = self._create_container(public_url, caption)
            self._wait_for_container(container_id)
            self._publish_container(container_id)
            return UploadResult(
                file_path=file_path,
                platform="instagram",
                status="success",
                publish_id=container_id,
                timestamp=ts,
            )
        except _RateLimitError:
            # exponential backoff retries
            for wait in (15, 30, 60):
                time.sleep(wait)
                try:
                    container_id = self._create_container(public_url, caption)
                    self._wait_for_container(container_id)
                    self._publish_container(container_id)
                    return UploadResult(
                        file_path=file_path,
                        platform="instagram",
                        status="success",
                        publish_id=container_id,
                        timestamp=ts,
                    )
                except _RateLimitError:
                    continue
            return UploadResult(
                file_path=file_path,
                platform="instagram",
                status="failed",
                error_code="rate_limit",
                error_message="Rate limit exceeded after retries",
                timestamp=ts,
            )
        except Exception as exc:
            return UploadResult(
                file_path=file_path,
                platform="instagram",
                status="failed",
                error_code="upload_error",
                error_message=str(exc),
                timestamp=ts,
            )

    # ------------------------------------------------------------------

    def _create_container(self, video_url: str, caption: str) -> str:
        resp = requests.post(
            f"{API_BASE}/{self.ig_user_id}/media",
            json={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": True,
                "access_token": self.access_token,
            },
            timeout=60,
        )
        self._check_response(resp)
        return resp.json()["id"]

    def _wait_for_container(self, container_id: str, timeout: int = 300) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(10)
            resp = requests.get(
                f"{API_BASE}/{container_id}",
                params={"fields": "status_code,status", "access_token": self.access_token},
                timeout=30,
            )
            self._check_response(resp)
            data = resp.json()
            status_code = data.get("status_code", "")
            if status_code == "FINISHED":
                return
            if status_code == "ERROR":
                raise RuntimeError(
                    f"Instagram container processing failed: {data.get('status', 'unknown error')}"
                )
            if status_code == "EXPIRED":
                raise RuntimeError("Instagram media container expired before publishing.")
        raise TimeoutError(
            f"Container {container_id} did not finish processing within {timeout}s."
        )

    def _publish_container(self, container_id: str) -> None:
        resp = requests.post(
            f"{API_BASE}/{self.ig_user_id}/media_publish",
            json={"creation_id": container_id, "access_token": self.access_token},
            timeout=30,
        )
        self._check_response(resp)

    @staticmethod
    def _check_response(resp: requests.Response) -> None:
        if resp.status_code == 429:
            raise _RateLimitError()
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise RuntimeError(f"Instagram API error (HTTP {resp.status_code}): {body}")


class _RateLimitError(Exception):
    pass
