from __future__ import annotations

import platform
from pathlib import Path


def banglish_data_dir(addon_dir: Path) -> Path:
    system = platform.system()
    if system == "Darwin":
        path = Path.home() / "Library" / "Application Support" / "BanGlish"
    elif system == "Windows":
        appdata = Path.home()
        base = Path.home()
        if "APPDATA" in __import__("os").environ:
            base = Path(__import__("os").environ["APPDATA"])
        path = base / "BanGlish"
    else:
        xdg = __import__("os").environ.get("XDG_DATA_HOME")
        if xdg:
            path = Path(xdg) / "BanGlish"
        else:
            path = Path.home() / ".local" / "share" / "BanGlish"
    path.mkdir(parents=True, exist_ok=True)
    return path


def corpus_db_path(addon_dir: Path) -> Path:
    return banglish_data_dir(addon_dir) / "kimchi_corpus.sqlite3"


def subtitle_cache_dir(addon_dir: Path) -> Path:
    path = banglish_data_dir(addon_dir) / "kimchi_subtitles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def audio_cache_dir(addon_dir: Path) -> Path:
    path = banglish_data_dir(addon_dir) / "audio_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path(addon_dir: Path) -> Path:
    return banglish_data_dir(addon_dir) / "banglish.log"


def deepl_key_path(addon_dir: Path) -> Path:
    return banglish_data_dir(addon_dir) / "deepl_api_key.txt"


def translation_cache_path(addon_dir: Path) -> Path:
    return banglish_data_dir(addon_dir) / "translation_cache.json"
