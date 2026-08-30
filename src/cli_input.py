"""Reading a question line from stdin with legacy-encoding fallback.

Extracted from main.py so unit tests can exercise it without importing the
heavy assistant stack (Ollama, FAISS). Terminals configured for a legacy
Cyrillic encoding (e.g. Windows-1251) send bytes that are invalid UTF-8;
forcing UTF-8 turns them into U+FFFD and the CLI used to ask to retype
forever. Raw bytes are decoded UTF-8 first, then cp1251; bytes no known
encoding fits still ask for a retype.
"""

import sys
from typing import BinaryIO

# First encoding that can decode the raw bytes wins. cp1251 covers legacy
# Cyrillic terminals; koi8-r and friends are intentionally not guessed.
_INPUT_ENCODINGS = ("utf-8", "cp1251")

# Module-level so tests can reset it; one warning per session is enough.
_warned_non_utf8 = False


def _decode_raw_line(raw: bytes) -> tuple[str, str]:
    """Decode one raw input line.

    Returns (text, encoding) where encoding is the encoding that decoded the
    bytes ("utf-8", "cp1251") or "undecodable" when none fit and replacement
    characters had to be used.
    """
    for encoding in _INPUT_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "undecodable"


def _warn_legacy_encoding(encoding: str) -> None:
    """Print a one-time hint that stdin is not delivering UTF-8 bytes."""
    global _warned_non_utf8
    if _warned_non_utf8:
        return
    _warned_non_utf8 = True
    print(
        f"⚠️  Input is not UTF-8; decoded as {encoding}. "
        "If text looks wrong, set your terminal encoding to UTF-8."
    )


def _read_question_fallback() -> str | None:
    """Legacy text-mode path for exotic embeddings without sys.stdin.buffer."""
    try:
        query = input("❓ Question: ").strip()
    except UnicodeDecodeError:
        print("⚠️  Input could not be decoded as UTF-8, please retype the question")
        return ""
    except EOFError:
        return None
    if "\ufffd" in query:
        print("⚠️  Input contained invalid UTF-8 bytes, please retype the question")
        return ""
    return query


def read_question(stream: BinaryIO | None = None) -> str | None:
    """Read one question line from binary stdin.

    Returns the stripped text, an empty string if the line could not be
    decoded (user is asked to retry), or None on EOF (Ctrl+D).
    """
    src = stream if stream is not None else getattr(sys.stdin, "buffer", None)
    if src is None:
        return _read_question_fallback()

    print("❓ Question: ", end="", flush=True)
    raw = src.readline()
    if not raw:
        return None

    text, encoding = _decode_raw_line(raw)
    text = text.strip()

    if encoding == "undecodable":
        print("⚠️  Input contained invalid UTF-8 bytes, please retype the question")
        return ""
    if encoding != "utf-8" and text:
        _warn_legacy_encoding(encoding)
    return text
