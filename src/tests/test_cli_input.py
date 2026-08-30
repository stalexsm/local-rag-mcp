"""Question-reading seam (cli_input.read_question, cli_input._decode_raw_line).

Raw bytes from stdin are decoded UTF-8 first; legacy Cyrillic terminals
sending cp1251 bytes fall back to cp1251 with a one-time warning instead of
an endless "invalid UTF-8, please retype" loop. Bytes no known encoding fits
ask for a retype. No Ollama, no FAISS: input arrives as BytesIO.
"""

import io
import sys

import pytest

from cli_input import _decode_raw_line, read_question


@pytest.fixture(autouse=True)
def _reset_warning_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cli_input._warned_non_utf8", False)


def test_utf8_line_decodes_with_no_fallback() -> None:
    assert _decode_raw_line("Как дела?\n".encode()) == ("Как дела?\n", "utf-8")


def test_cp1251_line_falls_back_to_cp1251() -> None:
    assert _decode_raw_line("Как дела?\n".encode("cp1251")) == (
        "Как дела?\n",
        "cp1251",
    )


def test_undecodable_bytes_are_reported() -> None:
    text, encoding = _decode_raw_line(b"\x98\n")
    assert encoding == "undecodable"
    assert "\ufffd" in text


def test_reads_utf8_question_without_warning(capsys: pytest.CaptureFixture[str]) -> None:
    assert read_question(io.BytesIO("Как дела?\n".encode())) == "Как дела?"
    assert "not UTF-8" not in capsys.readouterr().out


def test_reads_cp1251_question_with_warning(capsys: pytest.CaptureFixture[str]) -> None:
    raw = io.BytesIO("Как дела?\n".encode("cp1251"))
    assert read_question(raw) == "Как дела?"
    assert "cp1251" in capsys.readouterr().out


def test_warning_is_printed_only_once(capsys: pytest.CaptureFixture[str]) -> None:
    raw = io.BytesIO("Как дела?\nКак дела?\n".encode("cp1251"))
    assert read_question(raw) == "Как дела?"
    assert read_question(raw) == "Как дела?"
    assert capsys.readouterr().out.count("not UTF-8") == 1


def test_eof_returns_none() -> None:
    assert read_question(io.BytesIO(b"")) is None


def test_undecodable_line_asks_to_retype(capsys: pytest.CaptureFixture[str]) -> None:
    assert read_question(io.BytesIO(b"\x98\n")) == ""
    assert "invalid" in capsys.readouterr().out


def test_strips_surrounding_whitespace() -> None:
    assert read_question(io.BytesIO("  привет  \n".encode())) == "привет"


def test_fallback_eof_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_eof(prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr(sys, "stdin", object())  # no .buffer → text-mode fallback
    monkeypatch.setattr("builtins.input", raise_eof)
    assert read_question() is None


def test_fallback_undecodable_asks_to_retype(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", object())  # no .buffer → text-mode fallback
    monkeypatch.setattr("builtins.input", lambda prompt="": "\ufffd")
    assert read_question() == ""
    assert "invalid" in capsys.readouterr().out
