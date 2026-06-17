"""Single-instance lock for the GUI tray app."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from chaseos.storage.paths import get_single_instance_lock_path


@dataclass
class SingleInstanceGuard:
    """File-based GUI instance guard with stale lock cleanup."""

    base_path: Path | str | None = None

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_path) if self.base_path is not None else None
        self.path = get_single_instance_lock_path(self.base_path)
        self.acquired = False

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self._lock_is_active():
            return False
        if self.path.exists():
            self.path.unlink()
        payload = {
            "pid": os.getpid(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.acquired = True
        return True

    def release(self) -> None:
        if self.acquired and self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                payload = {}
            if payload.get("pid") == os.getpid():
                self.path.unlink()
        self.acquired = False

    def _lock_is_active(self) -> bool:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            pid = int(payload["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            return False
        if pid == os.getpid():
            return True
        return _pid_exists(pid)


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if platform.system() == "Windows":
        return _windows_pid_exists(pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _windows_pid_exists(pid: int) -> bool:
    try:
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information,
            False,
            pid,
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    except (AttributeError, OSError, ValueError):
        return False
