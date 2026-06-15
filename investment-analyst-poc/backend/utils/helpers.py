"""Misc helper utilities."""
from __future__ import annotations
from typing import Iterable, List
import re


def sanitize_text(text: str) -> str:
    """Basic sanitization to avoid prompt injection and control chars."""
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    return text.strip()


def chunk_text(text: str, max_tokens: int = 800) -> List[str]:
    """Naive chunking by words aiming for ~max_tokens chunks.

    This is token-approx via words for simplicity in POC.
    """
    words = text.split()
    chunks: List[str] = []
    buf: List[str] = []
    for w in words:
        buf.append(w)
        if len(buf) >= max_tokens:
            chunks.append(" ".join(buf))
            buf = []
    if buf:
        chunks.append(" ".join(buf))
    return chunks


def clamp(n: float, low: float, high: float) -> float:
    return max(low, min(n, high))
