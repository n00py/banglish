from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from urllib.request import urlopen

from ..config import AddonConfig
from ..corpus.api import KimchiCorpusAPIServer
from ..corpus.db import KimchiCorpusDatabase
from ..corpus.ingest import KimchiCorpusIngestor


_RUNTIME_LOCK = threading.Lock()
_RUNTIME_SERVER: KimchiCorpusAPIServer | None = None
_RUNTIME_THREAD: threading.Thread | None = None


def ensure_local_api_started(
    addon_dir: Path,
    config: AddonConfig,
    logger: logging.Logger | None = None,
) -> None:
    global _RUNTIME_SERVER, _RUNTIME_THREAD
    logger = logger or logging.getLogger(__name__)
    with _RUNTIME_LOCK:
        if _RUNTIME_THREAD is not None and _RUNTIME_THREAD.is_alive():
            return
        host, port = _host_port_from_base_url(config.local_api_base_url)
        db = KimchiCorpusDatabase(addon_dir / "user_files" / "kimchi_corpus.sqlite3", logger=logger)
        ingestor = KimchiCorpusIngestor(addon_dir, db, logger=logger)
        _RUNTIME_SERVER = KimchiCorpusAPIServer(
            addon_dir=addon_dir,
            db=db,
            ingestor=ingestor,
            logger=logger,
            host=host,
            port=port,
        )
        _RUNTIME_THREAD = threading.Thread(
            target=_RUNTIME_SERVER.serve_forever,
            name="kimchi-local-api",
            daemon=True,
        )
        _RUNTIME_THREAD.start()
    _wait_for_health(config.local_api_base_url, timeout_seconds=config.local_api_timeout_seconds)


def _host_port_from_base_url(base_url: str) -> tuple[str, int]:
    value = base_url.replace("http://", "").replace("https://", "").strip("/")
    if ":" in value:
        host, port_text = value.rsplit(":", 1)
        try:
            return host, int(port_text)
        except ValueError:
            return host, 8765
    return value, 8765


def _wait_for_health(base_url: str, timeout_seconds: int) -> None:
    deadline = time.time() + max(1, timeout_seconds)
    health_url = base_url.rstrip("/") + "/health"
    while time.time() < deadline:
        try:
            with urlopen(health_url, timeout=1):
                return
        except Exception:
            time.sleep(0.1)
