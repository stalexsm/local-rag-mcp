"""Keyword-parsing seam (rag.expansion.parse_keywords).

Pure fallback policy at the LLM boundary: a raw answer string becomes a
clean keyword list; an empty or missing answer degrades to [] — search
proceeds on the bare question. No Ollama, no HTTP: expand_query wraps this
seam and owns the degradation of transport failures itself.
"""

from rag.expansion import parse_keywords


def test_splits_trims_and_drops_empty_parts() -> None:
    assert parse_keywords("отпуск, больничный,,  remote  work ,") == [
        "отпуск",
        "больничный",
        "remote  work",
    ]


def test_missing_answer_yields_empty_list() -> None:
    assert parse_keywords(None) == []


def test_empty_or_blank_answer_yields_empty_list() -> None:
    assert parse_keywords("") == []
    assert parse_keywords("   ") == []


def test_duplicates_keep_first_occurrence() -> None:
    assert parse_keywords("отпуск, отпуск, больничный, отпуск") == ["отпуск", "больничный"]


def test_keywords_capped_at_limit() -> None:
    raw = ",".join(f"kw{i}" for i in range(10))
    assert parse_keywords(raw, limit=8) == [f"kw{i}" for i in range(8)]
