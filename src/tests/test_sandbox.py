"""Document sandbox seam (sandbox.is_within): a file path in, a verdict out.

The contract under test: a path may be read only if it resolves inside the
documents directory. A string-prefix check (startswith) is not enough —
"…/docs-evil/x" starts with "…/docs" — so the decision compares resolved
paths structurally (Path.is_relative_to). Regression coverage for issue #9.
"""

from pathlib import Path

import pytest

from sandbox import is_within


@pytest.fixture()
def base(tmp_path: Path) -> Path:
    """A documents directory with one file, plus a sibling "<base>-evil"."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "hello.md").write_text("inside", encoding="utf-8")

    evil = tmp_path / "docs-evil"
    evil.mkdir()
    (evil / "secret.md").write_text("sibling escape", encoding="utf-8")
    return docs


def test_relative_path_resolves_against_cwd(base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Relative paths resolve against the CWD (how the assistant calls us:
    it passes "docs/…" and the server runs with CWD = src/), not against
    the base directory itself."""
    monkeypatch.chdir(base)
    assert is_within("hello.md", base)
    assert not is_within("../docs-evil/secret.md", base)


def test_absolute_path_inside_base_is_allowed(base: Path) -> None:
    assert is_within(base / "hello.md", base)


def test_sibling_directory_is_denied(base: Path) -> None:
    """The issue #9 regression: "<base>-evil/…" starts with "<base"."""
    evil = base.with_name(base.name + "-evil") / "secret.md"
    assert evil.exists()
    assert not is_within(evil, base)


def test_parent_traversal_is_denied(base: Path) -> None:
    assert not is_within(base / ".." / "docs-evil" / "secret.md", base)


def test_absolute_path_outside_base_is_denied(base: Path) -> None:
    assert not is_within("/etc/hosts", base)


def test_symlink_escape_is_denied(base: Path, tmp_path: Path) -> None:
    """resolve() follows symlinks, so a link must not open a way out."""
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    link = base / "link.md"
    link.symlink_to(outside)
    assert not is_within(link, base)


def test_base_itself_counts_as_inside(base: Path) -> None:
    """The base directory is inside by definition (open() fails on it later)."""
    assert is_within(base, base)
