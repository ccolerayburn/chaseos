"""Daily startup ritual session persistence."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from chaseos.storage.paths import get_daily_session_path


class DailySessionRecord(BaseModel):
    """Restart-safe daily ritual state without raw private check-in text."""

    date: date
    started_at: datetime
    updated_at: datetime
    current_stage: str
    startup_mode: str = "Structured Start"
    practical_signals: dict[str, Any] = Field(default_factory=dict)
    theme_plan_summary: str | None = None
    theme_approved: bool = False
    innovation_takeaway: str | None = None
    poster_approved: bool = False
    generated_assets: dict[str, str] = Field(default_factory=dict)
    wallpaper_manifest_path: str | None = None
    preflight_status: str | None = None
    dry_run_status: str | None = None
    applied_status: str | None = None
    last_error: str | None = None


class DailySessionStore:
    """Load and save today's daily startup ritual record."""

    def __init__(self, base_path: Path | str | None = None) -> None:
        self.base_path = Path(base_path) if base_path is not None else None

    def path(self, run_date: date | None = None) -> Path:
        return get_daily_session_path(run_date=run_date, base_path=self.base_path)

    def exists(self, run_date: date | None = None) -> bool:
        return self.path(run_date).exists()

    def load(self, run_date: date | None = None) -> DailySessionRecord | None:
        path = self.path(run_date)
        if not path.exists():
            return None
        return DailySessionRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, record: DailySessionRecord) -> DailySessionRecord:
        record.updated_at = datetime.now(UTC)
        path = self.path(record.date)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return record
