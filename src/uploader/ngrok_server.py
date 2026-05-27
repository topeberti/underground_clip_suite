"""
src/uploader/ngrok_server.py — Local HTTP server + ngrok tunnel lifecycle.

Used by the Instagram uploader because the Graph API requires a publicly
accessible HTTPS video URL rather than accepting file uploads directly.
"""

import subprocess
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class NgrokServer:
    """
    Serves a local folder over HTTP and exposes it via an ngrok HTTPS tunnel.

    Usage:
        server = NgrokServer()
        public_url = server.start(folder_path)   # e.g. "https://abc123.ngrok-free.app"
        video_url = f"{public_url}/my_video.mp4"
        ...
        server.stop()
    """

    PORT = 8765

    def __init__(self):
        self._http_server: HTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self._ngrok_proc: subprocess.Popen | None = None
        self.public_url: str = ""

    def start(self, folder: Path) -> str:
        self._start_http_server(folder)
        self.public_url = self._start_ngrok()
        return self.public_url

    def stop(self) -> None:
        if self._ngrok_proc:
            self._ngrok_proc.terminate()
            try:
                self._ngrok_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ngrok_proc.kill()
            self._ngrok_proc = None

        if self._http_server:
            self._http_server.shutdown()
            self._http_server = None

        if self._http_thread:
            self._http_thread.join(timeout=5)
            self._http_thread = None

        self.public_url = ""

    # ------------------------------------------------------------------

    def _start_http_server(self, folder: Path) -> None:
        class _Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(folder), **kwargs)

            def log_message(self, *args):
                pass  # suppress access logs

        self._http_server = HTTPServer(("localhost", self.PORT), _Handler)
        self._http_thread = threading.Thread(
            target=self._http_server.serve_forever, daemon=True
        )
        self._http_thread.start()

    def _start_ngrok(self) -> str:
        import shutil
        if not shutil.which("ngrok"):
            raise FileNotFoundError(
                "ngrok not found on PATH.\n"
                "Install it: choco install ngrok  OR  download from https://ngrok.com/download\n"
                "Then run once: ngrok config add-authtoken YOUR_TOKEN"
            )

        self._ngrok_proc = subprocess.Popen(
            ["ngrok", "http", str(self.PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Poll ngrok's local API until the tunnel is ready
        import requests
        deadline = time.time() + 15
        while time.time() < deadline:
            time.sleep(1)
            try:
                resp = requests.get("http://localhost:4040/api/tunnels", timeout=3)
                tunnels = resp.json().get("tunnels", [])
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        return tunnel["public_url"].rstrip("/")
            except Exception:
                pass

        raise RuntimeError(
            "ngrok tunnel did not start within 15 seconds. "
            "Check that your ngrok authtoken is configured: ngrok config add-authtoken YOUR_TOKEN"
        )
