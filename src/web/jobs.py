"""
src/web/jobs.py — In-memory background job manager.

Each job runs in its own thread. Output printed to the job's rich Console is
captured into a line buffer that the SSE endpoint streams to the browser.
"""

import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from rich.console import Console

MAX_JOBS = 50


class _LogWriter:
    """File-like object that splits written text into lines on the owning job."""

    def __init__(self, job: "Job"):
        self._job = job
        self._partial = ""

    def write(self, text: str) -> int:
        self._partial += text
        *lines, self._partial = self._partial.split("\n")
        for line in lines:
            self._job.log.append(line.rstrip("\r"))
        return len(text)

    def flush(self) -> None:
        if self._partial:
            self._job.log.append(self._partial)
            self._partial = ""

    def isatty(self) -> bool:
        return False


@dataclass
class Job:
    id: str
    kind: str
    title: str
    status: str = "running"          # running | done | failed
    log: list[str] = field(default_factory=list)
    done: int = 0
    total: int = 0
    result: Any = None
    error: str = ""
    started: float = field(default_factory=time.time)

    def summary(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "title": self.title, "status": self.status,
            "done": self.done, "total": self.total, "error": self.error,
            "result": self.result, "started": self.started,
        }


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()
_exclusive = threading.Lock()  # held while a GPU-heavy job (tagging) runs


class Busy(Exception):
    pass


def start_job(
    kind: str,
    title: str,
    fn: Callable[[Console, Callable[[int, int], None]], Any],
    exclusive: bool = False,
) -> Job:
    """Run fn(console, on_progress) in a thread. Raises Busy if exclusive and one is already running."""
    if exclusive and not _exclusive.acquire(blocking=False):
        raise Busy("Another tagging job is already running.")

    job = Job(id=uuid.uuid4().hex[:12], kind=kind, title=title)
    writer = _LogWriter(job)
    console = Console(file=writer, force_terminal=False, color_system=None, width=120)

    def on_progress(done: int, total: int) -> None:
        job.done, job.total = done, total

    def runner() -> None:
        try:
            job.result = fn(console, on_progress)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 — surfaced to the UI
            job.error = str(exc) or exc.__class__.__name__
            if isinstance(exc, (RuntimeError, ValueError, FileNotFoundError, TimeoutError)):
                job.log.append(f"Error: {job.error}")   # expected, user-actionable
            else:
                job.log.append(traceback.format_exc())
            job.status = "failed"
        finally:
            writer.flush()
            if exclusive:
                _exclusive.release()

    with _jobs_lock:
        _jobs[job.id] = job
        while len(_jobs) > MAX_JOBS:
            oldest = next((k for k, j in _jobs.items() if j.status != "running"), None)
            if oldest is None:
                break
            del _jobs[oldest]

    threading.Thread(target=runner, daemon=True).start()
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def list_jobs() -> list[dict]:
    return [j.summary() for j in reversed(list(_jobs.values()))]


def stream(job: Job):
    """Yield SSE frames: 'log' events per line, 'progress', and a final 'end'."""
    import json

    sent = 0
    last_progress = None
    while True:
        lines = job.log[sent:]
        for line in lines:
            yield f"event: log\ndata: {json.dumps(line)}\n\n"
        sent += len(lines)

        progress = (job.done, job.total)
        if progress != last_progress:
            last_progress = progress
            yield f"event: progress\ndata: {json.dumps({'done': job.done, 'total': job.total})}\n\n"

        if job.status != "running" and sent >= len(job.log):
            yield f"event: end\ndata: {json.dumps(job.summary())}\n\n"
            return
        time.sleep(0.25)
