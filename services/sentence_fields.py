from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .sound_field import note_has_field, sound_tag


SENTENCE_KOREAN_FIELD = "Sentence Korean"
SENTENCE_ENGLISH_FIELD = "Sentence English"
SENTENCE_AUDIO_FIELD = "Sentence Audio"
SENTENCE_FIELD_NAMES = (
    SENTENCE_KOREAN_FIELD,
    SENTENCE_ENGLISH_FIELD,
    SENTENCE_AUDIO_FIELD,
)


@dataclass(frozen=True)
class SaveSentenceFieldsResult:
    success: bool
    message: str
    media_filename: str = ""


def note_has_sentence_fields(note: object) -> bool:
    return all(note_has_field(note, field_name) for field_name in SENTENCE_FIELD_NAMES)


def save_sentence_fields(
    *,
    note: object,
    col: object,
    clip_path: Path,
    korean_text: str,
    english_text: str,
) -> SaveSentenceFieldsResult:
    missing_fields = [field_name for field_name in SENTENCE_FIELD_NAMES if not note_has_field(note, field_name)]
    if missing_fields:
        return SaveSentenceFieldsResult(
            success=False,
            message="This note is missing: " + ", ".join(missing_fields) + ".",
        )
    if not clip_path.exists() or clip_path.stat().st_size <= 0:
        return SaveSentenceFieldsResult(
            success=False,
            message="The extracted audio clip does not exist anymore.",
        )
    if not korean_text.strip():
        return SaveSentenceFieldsResult(
            success=False,
            message="The selected Korean sentence is empty.",
        )
    if not english_text.strip():
        return SaveSentenceFieldsResult(
            success=False,
            message="An English translation is required before saving sentence fields.",
        )

    media = getattr(col, "media", None)
    add_file = getattr(media, "add_file", None)
    if not callable(add_file):
        return SaveSentenceFieldsResult(
            success=False,
            message="Anki media import is not available in this collection.",
        )

    try:
        media_filename = str(add_file(str(clip_path)))
    except Exception as exc:
        return SaveSentenceFieldsResult(
            success=False,
            message=f"Could not import the extracted audio clip: {exc}",
        )

    note[SENTENCE_KOREAN_FIELD] = korean_text.strip()
    note[SENTENCE_ENGLISH_FIELD] = english_text.strip()
    note[SENTENCE_AUDIO_FIELD] = sound_tag(media_filename)

    update_note = getattr(col, "update_note", None)
    flush = getattr(note, "flush", None)
    try:
        if callable(update_note):
            update_note(note)
        elif callable(flush):
            flush()
        else:
            return SaveSentenceFieldsResult(
                success=False,
                message="Anki note saving is not available in this context.",
                media_filename=media_filename,
            )
    except Exception as exc:
        return SaveSentenceFieldsResult(
            success=False,
            message=f"Could not save the sentence fields: {exc}",
            media_filename=media_filename,
        )

    note_id = getattr(note, "id", 0)
    get_note = getattr(col, "get_note", None)
    if note_id and callable(get_note):
        try:
            persisted_note = get_note(int(note_id))
        except Exception as exc:
            return SaveSentenceFieldsResult(
                success=False,
                message=f"Saved the note, but could not verify it afterward: {exc}",
                media_filename=media_filename,
            )
        if (
            str(persisted_note[SENTENCE_KOREAN_FIELD]).strip() != korean_text.strip()
            or str(persisted_note[SENTENCE_ENGLISH_FIELD]).strip() != english_text.strip()
            or str(persisted_note[SENTENCE_AUDIO_FIELD]).strip() != sound_tag(media_filename)
        ):
            return SaveSentenceFieldsResult(
                success=False,
                message="Tried to save the sentence fields, but the saved note did not match the new values.",
                media_filename=media_filename,
            )

    return SaveSentenceFieldsResult(
        success=True,
        message="Saved sentence audio, Korean, and English into the sentence fields.",
        media_filename=media_filename,
    )
