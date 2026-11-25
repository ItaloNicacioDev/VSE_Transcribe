"""Shared background-job storage for VSE_Transcribe.

Provides a single, module-level dict + lock used by both the transcription
and model-download operators so that cancel/timer logic operates on the same
state instead of duplicated, per-module copies.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def get_jobs() -> Dict[str, Dict[str, Any]]:
    """Return the internal job dict (caller should hold the lock if mutating)."""
    return _jobs


def get_lock() -> threading.Lock:
    """Return the lock guarding ``_jobs``."""
    return _lock


def set_job(job_id: str, **fields: Any) -> None:
    """Create or update a job entry under the shared lock."""
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)
        else:
            _jobs[job_id] = dict(fields)


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Return a shallow copy of a job, or ``None`` if absent."""
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job is not None else None


def pop_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Remove and return a job, or ``None`` if absent."""
    with _lock:
        return _jobs.pop(job_id, None)
