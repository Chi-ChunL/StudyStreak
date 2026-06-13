import os
import shutil
import sys
from pathlib import Path


APP_DIR_NAME = "StudyStreak"


def get_app_data_dir() -> Path:
    configured_dir = os.getenv("STUDYSTREAK_DATA_DIR")

    if configured_dir:
        data_dir = Path(configured_dir).expanduser()
    elif sys.platform.startswith("win"):
        base_dir = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        data_dir = Path(base_dir) / APP_DIR_NAME if base_dir else Path.home() / APP_DIR_NAME
    elif sys.platform == "darwin":
        data_dir = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        data_home = os.getenv("XDG_DATA_HOME")
        data_dir = Path(data_home) / APP_DIR_NAME if data_home else Path.home() / ".local" / "share" / APP_DIR_NAME

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_app_data_file(filename: str) -> Path:
    return get_app_data_dir() / filename


def migrate_legacy_file(filename: str, target_file: Path) -> None:
    legacy_file = Path(filename)

    if target_file.exists() or not legacy_file.exists():
        return

    try:
        if legacy_file.resolve() == target_file.resolve():
            return
    except OSError:
        return

    shutil.copy2(legacy_file, target_file)
