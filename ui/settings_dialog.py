from __future__ import annotations

from pathlib import Path
import json
from urllib.request import Request, urlopen

from aqt import mw
from aqt.qt import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    qconnect,
)
from aqt.utils import tooltip

from ..config import config_from_dict
from ..services.local_api_runtime import ensure_local_api_started
from ..services.translation_service import (
    clear_deepl_api_key,
    deepl_api_key_path,
    load_deepl_api_key,
    save_deepl_api_key,
)


def _addon_dir() -> Path:
    return Path(__file__).resolve().parent.parent


class DeepLSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent or mw)
        self._addon_dir = _addon_dir()
        self._config = config_from_dict(mw.addonManager.getConfig(__name__.split(".ui.")[0]) or {})
        self.setWindowTitle("BanGlish Context Settings")
        self.resize(680, 420)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Set your DeepL API key for English translations. "
            "The key is saved locally in this add-on's user_files folder and is not stored in git.",
            self,
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        path_label = QLabel(f"Local key file: {deepl_api_key_path(self._addon_dir)}", self)
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(path_label.textInteractionFlags())
        layout.addWidget(path_label)

        field_label = QLabel("DeepL API Key", self)
        layout.addWidget(field_label)

        field_row = QHBoxLayout()
        self.key_field = QLineEdit(self)
        self.key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_field.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx")
        self.key_field.setText(load_deepl_api_key(self._addon_dir))
        self.show_key_checkbox = QCheckBox("Show", self)
        qconnect(self.show_key_checkbox.toggled, self._toggle_key_visibility)
        field_row.addWidget(self.key_field, 1)
        field_row.addWidget(self.show_key_checkbox)
        layout.addLayout(field_row)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        self.status_label.setText(self._status_text())
        layout.addWidget(self.status_label)

        corpus_intro = QLabel(
            "Kimchi local corpus controls. The API runs locally and stores its SQLite database in this add-on's user_files folder.",
            self,
        )
        corpus_intro.setWordWrap(True)
        layout.addWidget(corpus_intro)

        self.corpus_status_label = QLabel(self)
        self.corpus_status_label.setWordWrap(True)
        self.corpus_status_label.setTextInteractionFlags(self.corpus_status_label.textInteractionFlags())
        layout.addWidget(self.corpus_status_label)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Save Key", self)
        self.clear_button = QPushButton("Clear Key", self)
        self.close_button = QPushButton("Close", self)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        corpus_button_row = QHBoxLayout()
        self.refresh_corpus_button = QPushButton("Refresh Corpus Status", self)
        self.backfill_button = QPushButton("Start/Resume Backfill", self)
        self.subtitle_recheck_button = QPushButton("Recheck Subtitles", self)
        corpus_button_row.addWidget(self.refresh_corpus_button)
        corpus_button_row.addWidget(self.backfill_button)
        corpus_button_row.addWidget(self.subtitle_recheck_button)
        corpus_button_row.addStretch(1)
        layout.addLayout(corpus_button_row)

        qconnect(self.save_button.clicked, self.save_key)
        qconnect(self.clear_button.clicked, self.clear_key)
        qconnect(self.close_button.clicked, self.accept)
        qconnect(self.refresh_corpus_button.clicked, self.refresh_corpus_status)
        qconnect(self.backfill_button.clicked, self.start_corpus_backfill)
        qconnect(self.subtitle_recheck_button.clicked, self.start_subtitle_recheck)

        self.refresh_corpus_status()

    def _toggle_key_visibility(self, checked: bool) -> None:
        self.key_field.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _status_text(self) -> str:
        key = load_deepl_api_key(self._addon_dir)
        if key:
            return "A DeepL key is saved locally for this add-on."
        return "No DeepL key is saved yet."

    def save_key(self) -> None:
        key_text = self.key_field.text().strip()
        if not key_text:
            self.status_label.setText("Enter a DeepL key first, or click Clear Key to remove the saved one.")
            return
        save_deepl_api_key(self._addon_dir, key_text)
        self.status_label.setText("Saved the DeepL key locally for this add-on.")
        tooltip("Saved DeepL key.")

    def clear_key(self) -> None:
        clear_deepl_api_key(self._addon_dir)
        self.key_field.clear()
        self.status_label.setText("Cleared the local DeepL key.")
        tooltip("Cleared DeepL key.")

    def refresh_corpus_status(self) -> None:
        try:
            payload = self._local_api_request("/health", method="GET")
        except Exception as exc:
            self.corpus_status_label.setText(
                "Kimchi corpus API is not reachable yet.\n"
                f"Local API: {self._config.local_api_base_url}\n"
                f"Database: {self._addon_dir / 'user_files' / 'kimchi_corpus.sqlite3'}\n"
                f"Error: {exc}"
            )
            return
        stats = payload.get("stats") or {}
        last_discovery = stats.get("last_discovery_run") or {}
        self.corpus_status_label.setText(
            "Local API: "
            + self._config.local_api_base_url
            + "\nDatabase: "
            + str(self._addon_dir / "user_files" / "kimchi_corpus.sqlite3")
            + "\nKimchi media: "
            + str(stats.get("kimchi_media", 0))
            + " | Videos: "
            + str(stats.get("youtube_videos", 0))
            + " | Ready subtitle videos: "
            + str(stats.get("eligible_videos", 0))
            + " | Subtitle cues: "
            + str(stats.get("subtitle_cues", 0))
            + (
                "\nLast discovery run: "
                + str(last_discovery.get("status", "n/a"))
                + " started "
                + str(last_discovery.get("started_at", ""))
                if last_discovery
                else ""
            )
        )

    def start_corpus_backfill(self) -> None:
        try:
            payload = self._local_api_request("/admin/discovery/backfill", method="POST")
        except Exception as exc:
            self.corpus_status_label.setText(f"Could not start corpus backfill: {exc}")
            return
        self.corpus_status_label.setText(
            "Kimchi corpus backfill request accepted.\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        tooltip("Kimchi corpus backfill started.")

    def start_subtitle_recheck(self) -> None:
        try:
            payload = self._local_api_request("/admin/subtitles/recheck", method="POST")
        except Exception as exc:
            self.corpus_status_label.setText(f"Could not start subtitle recheck: {exc}")
            return
        self.corpus_status_label.setText(
            "Kimchi subtitle recheck request accepted.\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        tooltip("Kimchi subtitle recheck started.")

    def _local_api_request(self, path: str, *, method: str) -> dict:
        ensure_local_api_started(self._addon_dir, self._config)
        request = Request(
            self._config.local_api_base_url.rstrip("/") + path,
            headers={"Accept": "application/json"},
            method=method,
        )
        with urlopen(request, timeout=max(1, self._config.local_api_timeout_seconds)) as response:
            return json.loads(response.read().decode("utf-8"))


def open_deepl_settings_dialog(parent=None) -> int:
    dialog = DeepLSettingsDialog(parent=parent or mw)
    return dialog.exec()
