"""Runtime storage path helpers."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

APP_LOCAL_DATA_DIR_NAME = "ChaseOS"


def get_chaseos_data_dir(base_path: Path | str | None = None) -> Path:
    """Return the ChaseOS runtime data directory."""

    if base_path is not None:
        return Path(base_path)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_LOCAL_DATA_DIR_NAME
    return Path.home() / "AppData" / "Local" / APP_LOCAL_DATA_DIR_NAME


def get_generated_dir(run_date: date, base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "generated" / run_date.isoformat()


def get_posters_dir(run_date: date, base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "posters" / run_date.isoformat()


def get_photo_index_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "photo_index"


def get_photo_index_path(base_path: Path | str | None = None) -> Path:
    return get_photo_index_dir(base_path) / "photo_index.json"


def get_config_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "config"


def get_monitor_mapping_path(base_path: Path | str | None = None) -> Path:
    return get_config_dir(base_path) / "monitor_mapping.json"


def get_sessions_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "sessions"


def get_daily_session_dir(
    run_date: date | None = None,
    base_path: Path | str | None = None,
) -> Path:
    run_date = run_date or date.today()
    return get_sessions_dir(base_path) / run_date.isoformat()


def get_daily_session_path(
    run_date: date | None = None,
    base_path: Path | str | None = None,
) -> Path:
    return get_daily_session_dir(run_date, base_path) / "daily_session.json"


def get_daily_summary_path(
    run_date: date | None = None,
    base_path: Path | str | None = None,
) -> Path:
    return get_daily_session_dir(run_date, base_path) / "daily_summary.txt"


def get_last_startup_smoke_text_path(base_path: Path | str | None = None) -> Path:
    return get_daily_session_dir(base_path=base_path) / "last_startup_smoke.txt"


def get_last_startup_smoke_json_path(base_path: Path | str | None = None) -> Path:
    return get_daily_session_dir(base_path=base_path) / "last_startup_smoke.json"


def get_logs_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "logs"


def get_runtime_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "runtime"


def get_single_instance_lock_path(base_path: Path | str | None = None) -> Path:
    return get_runtime_dir(base_path) / "chaseos.lock"


def get_exports_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "exports"


def get_release_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "release"


def get_last_release_smoke_text_path(base_path: Path | str | None = None) -> Path:
    return get_release_dir(base_path) / "last_release_smoke.txt"


def get_last_release_smoke_json_path(base_path: Path | str | None = None) -> Path:
    return get_release_dir(base_path) / "last_release_smoke.json"


def get_wallpaper_state_dir(base_path: Path | str | None = None) -> Path:
    return get_chaseos_data_dir(base_path) / "wallpaper_state"


def get_previous_wallpapers_path(base_path: Path | str | None = None) -> Path:
    return get_wallpaper_state_dir(base_path) / "previous_wallpapers.json"


def get_last_apply_manifest_path(base_path: Path | str | None = None) -> Path:
    return get_wallpaper_state_dir(base_path) / "last_apply_manifest.json"


def get_last_wallpaper_diagnostics_path(base_path: Path | str | None = None) -> Path:
    return get_wallpaper_state_dir(base_path) / "last_wallpaper_diagnostics.json"


def get_last_wallpaper_smoke_text_path(base_path: Path | str | None = None) -> Path:
    return get_wallpaper_state_dir(base_path) / "last_wallpaper_smoke.txt"


def get_last_wallpaper_smoke_json_path(base_path: Path | str | None = None) -> Path:
    return get_wallpaper_state_dir(base_path) / "last_wallpaper_smoke.json"
