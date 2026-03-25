from __future__ import annotations

import html
import json
import re
from collections import Counter
from typing import Iterable


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")


def clean_text(text: str) -> str:
    cleaned = TAG_RE.sub("", html.unescape(text or ""))
    return SPACE_RE.sub(" ", cleaned).strip()


def normalize_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", clean_text(text))


def tokenize_text(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(clean_text(text))]


def tokenized_text_blob(text: str) -> str:
    return " ".join(tokenize_text(text))


def dedupe_terms(texts: Iterable[str]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for text in texts:
        counter.update(tokenize_text(text))
    return dict(counter)


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
