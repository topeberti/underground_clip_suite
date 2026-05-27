"""
src/uploader/auth.py — OAuth token management for TikTok and Instagram.

Handles loading/saving config, token refresh, and first-time OAuth flows.
"""

import json
import os
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

CONFIG_EXAMPLE = Path(__file__).parent.parent.parent / "config" / "upload_config.json.example"
OAUTH_PORT = 8080
OAUTH_REDIRECT = f"http://localhost:{OAUTH_PORT}/callback"


class AuthExpiredError(Exception):
    pass


# ---------------------------------------------------------------------------
# Config load / save
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Upload config not found at {config_path}\n"
            f"Copy {CONFIG_EXAMPLE} to {config_path} and fill in your app credentials,\n"
            "then run: python src/main.py setup-upload"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config_path: Path, config: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = config_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    tmp.replace(config_path)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _is_expired(expires_at: str, buffer_seconds: int = 300) -> bool:
    if not expires_at:
        return True
    try:
        expiry = datetime.fromisoformat(expires_at)
        return datetime.now() >= expiry - timedelta(seconds=buffer_seconds)
    except ValueError:
        return True


def ensure_tiktok_token(config: dict, config_path: Path) -> str:
    tk = config.get("tiktok", {})
    if not tk.get("access_token"):
        raise AuthExpiredError(
            "TikTok access token missing. Run: python src/main.py setup-upload --platform tiktok"
        )
    if not _is_expired(tk.get("expires_at", "")):
        return tk["access_token"]

    # Attempt refresh
    refresh_token = tk.get("refresh_token", "")
    if not refresh_token:
        raise AuthExpiredError(
            "TikTok token expired and no refresh token available.\n"
            "Run: python src/main.py setup-upload --platform tiktok"
        )
    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key": tk["client_key"],
            "client_secret": tk["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise AuthExpiredError(
            f"TikTok token refresh failed ({resp.status_code}). "
            "Run: python src/main.py setup-upload --platform tiktok"
        )
    data = resp.json()
    config["tiktok"]["access_token"] = data["access_token"]
    config["tiktok"]["refresh_token"] = data.get("refresh_token", refresh_token)
    config["tiktok"]["expires_at"] = (
        datetime.now() + timedelta(seconds=data["expires_in"])
    ).isoformat()
    save_config(config_path, config)
    return config["tiktok"]["access_token"]


def ensure_instagram_token(config: dict, config_path: Path) -> str:  # noqa: ARG001
    ig = config.get("instagram", {})
    if not ig.get("access_token"):
        raise AuthExpiredError(
            "Instagram access token missing. Run: python src/main.py setup-upload --platform instagram"
        )
    if _is_expired(ig.get("expires_at", "")):
        raise AuthExpiredError(
            "Instagram token expired (tokens last 60 days and cannot be auto-refreshed).\n"
            "Run: python src/main.py setup-upload --platform instagram"
        )
    return ig["access_token"]


# ---------------------------------------------------------------------------
# OAuth callback server (shared by both platforms)
# ---------------------------------------------------------------------------

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            _OAuthCallbackHandler.code = params["code"][0]
        elif "error" in params:
            _OAuthCallbackHandler.error = params.get("error_description", params.get("error", ["Unknown error"]))[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Authentication successful!</h2>"
            b"<p>You can close this tab and return to your terminal.</p></body></html>"
        )

    def log_message(self, *args):  # suppress default access logs
        pass


def _wait_for_oauth_code(timeout: int = 120) -> str:
    _OAuthCallbackHandler.code = None
    _OAuthCallbackHandler.error = None
    server = HTTPServer(("localhost", OAUTH_PORT), _OAuthCallbackHandler)
    server.timeout = 1

    deadline = time.time() + timeout
    while time.time() < deadline:
        server.handle_request()
        if _OAuthCallbackHandler.code:
            server.server_close()
            return _OAuthCallbackHandler.code
        if _OAuthCallbackHandler.error:
            server.server_close()
            raise RuntimeError(f"OAuth denied: {_OAuthCallbackHandler.error}")
    server.server_close()
    raise TimeoutError("OAuth callback timed out after 2 minutes.")


# ---------------------------------------------------------------------------
# TikTok OAuth flow
# ---------------------------------------------------------------------------

def run_tiktok_oauth(config_path: Path) -> None:
    config = load_config(config_path)
    tk = config.get("tiktok", {})
    client_key = tk.get("client_key", "")
    client_secret = tk.get("client_secret", "")
    if not client_key or client_key.startswith("YOUR_"):
        raise ValueError(
            f"TikTok client_key not set in {config_path}. "
            "Fill in your app credentials first."
        )

    import secrets
    state = secrets.token_urlsafe(16)
    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/?"
        + urlencode({
            "client_key": client_key,
            "scope": "video.upload",
            "response_type": "code",
            "redirect_uri": OAUTH_REDIRECT,
            "state": state,
        })
    )
    print(f"\nOpening browser for TikTok authentication...\n{auth_url}\n")
    webbrowser.open(auth_url)

    code = _wait_for_oauth_code()

    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": OAUTH_REDIRECT,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    config["tiktok"]["access_token"] = data["access_token"]
    config["tiktok"]["refresh_token"] = data.get("refresh_token", "")
    config["tiktok"]["expires_at"] = (
        datetime.now() + timedelta(seconds=data["expires_in"])
    ).isoformat()
    config["tiktok"]["open_id"] = data.get("open_id", "")
    save_config(config_path, config)
    print("TikTok authentication saved.")


# ---------------------------------------------------------------------------
# Instagram OAuth flow
# ---------------------------------------------------------------------------

def run_instagram_oauth(config_path: Path) -> None:
    config = load_config(config_path)
    ig = config.get("instagram", {})
    app_id = ig.get("app_id", "")
    app_secret = ig.get("app_secret", "")
    if not app_id or app_id.startswith("YOUR_"):
        raise ValueError(
            f"Instagram app_id not set in {config_path}. "
            "Fill in your app credentials first."
        )

    auth_url = (
        "https://www.facebook.com/dialog/oauth?"
        + urlencode({
            "client_id": app_id,
            "redirect_uri": OAUTH_REDIRECT,
            "scope": "instagram_basic,instagram_content_publish,pages_read_engagement",
            "response_type": "code",
        })
    )
    print(f"\nOpening browser for Instagram/Meta authentication...\n{auth_url}\n")
    webbrowser.open(auth_url)

    code = _wait_for_oauth_code()

    # Exchange for short-lived token
    resp = requests.get(
        "https://graph.facebook.com/v22.0/oauth/access_token",
        params={
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": OAUTH_REDIRECT,
            "code": code,
        },
        timeout=30,
    )
    resp.raise_for_status()
    short_token = resp.json()["access_token"]

    # Exchange for long-lived token (60 days)
    resp2 = requests.get(
        "https://graph.facebook.com/v22.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )
    resp2.raise_for_status()
    data2 = resp2.json()
    long_token = data2["access_token"]
    expires_in = data2.get("expires_in", 5184000)  # default 60 days

    # Fetch ig_user_id
    resp3 = requests.get(
        "https://graph.facebook.com/v22.0/me/accounts",
        params={"fields": "instagram_business_account", "access_token": long_token},
        timeout=30,
    )
    resp3.raise_for_status()
    accounts = resp3.json().get("data", [])
    ig_user_id = ""
    for acc in accounts:
        if "instagram_business_account" in acc:
            ig_user_id = acc["instagram_business_account"]["id"]
            break
    if not ig_user_id:
        print(
            "Warning: could not automatically detect Instagram Business Account ID.\n"
            "Make sure your Instagram account is a Business or Creator account linked to a Facebook Page.\n"
            "You can set ig_user_id manually in the config file."
        )

    config["instagram"]["access_token"] = long_token
    config["instagram"]["expires_at"] = (
        datetime.now() + timedelta(seconds=expires_in)
    ).isoformat()
    config["instagram"]["ig_user_id"] = ig_user_id
    save_config(config_path, config)
    print(f"Instagram authentication saved. ig_user_id: {ig_user_id or '(not detected — set manually)'}")
