"""Settings persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path

from chaseos.models.monitor import MonitorLayout, MonitorMappingConfig
from chaseos.storage.paths import get_monitor_mapping_path


class MonitorMappingStore:
    """Persist monitor role mappings in ChaseOS local config."""

    def __init__(self, base_path: Path | str | None = None) -> None:
        self.base_path = Path(base_path) if base_path is not None else None

    @property
    def path(self) -> Path:
        return get_monitor_mapping_path(self.base_path)

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> MonitorMappingConfig | None:
        if not self.path.exists():
            return None
        return MonitorMappingConfig.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, config: MonitorMappingConfig) -> MonitorMappingConfig:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(config.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return config

    def save_layout(self, layout: MonitorLayout) -> MonitorMappingConfig:
        config = MonitorMappingConfig(
            assignments=layout.assignments,
            source="saved",
            notes=layout.warnings,
        )
        return self.save(config)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
