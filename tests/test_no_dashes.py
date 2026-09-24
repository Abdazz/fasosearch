"""Guard test: no em dash (U+2014) or en dash (U+2013) in git-tracked source code."""

import subprocess
from pathlib import Path

import pytest


def is_excluded(rel_path: str) -> bool:
    """Check if a repo-relative path should be excluded from the dash check.

    Args:
        rel_path: Repository-relative path as returned by `git ls-files`.

    Returns:
        True if the file should be excluded, False otherwise.
    """
    # Exclude top-level data/ directory
    if rel_path.startswith("data/"):
        return True

    # Exclude .xlsx files
    if rel_path.endswith(".xlsx"):
        return True

    # Exclude frontend/package-lock.json specifically
    if rel_path == "frontend/package-lock.json":
        return True

    return False


def test_is_excluded_filtering():
    """Unit tests for the is_excluded() helper."""
    # Should be excluded
    assert is_excluded("data/x.txt")
    assert is_excluded("data/subdir/file.py")
    assert is_excluded("something.xlsx")
    assert is_excluded("dir/file.xlsx")
    assert is_excluded("frontend/package-lock.json")

    # Should NOT be excluded
    assert not is_excluded("backend/app/data/x.py")
    assert not is_excluded("backend/app/corpus.py")
    assert not is_excluded("tests/test_no_dashes.py")
    assert not is_excluded("frontend/src/index.ts")
    assert not is_excluded("package.json")


def test_no_dashes_in_source_code():
    """No em dash (U+2014) or en dash (U+2013) should appear in source files."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("git not available")

    git_files = result.stdout.strip().split("\n")
    repo_root = Path(__file__).resolve().parent.parent

    violations = []

    for rel_path in git_files:
        # Skip excluded files
        if is_excluded(rel_path):
            continue

        file_path = repo_root / rel_path

        # Try to read file as UTF-8
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            # Ignore binary files and missing files
            continue

        # Check for em dash (U+2014) and en dash (U+2013)
        for line_num, line in enumerate(content.split("\n"), start=1):
            if "\u2014" in line or "\u2013" in line:
                violations.append(f"{rel_path}:{line_num}")

    if violations:
        pytest.fail(
            "Found em dash (\\u2014, U+2014) or en dash (\\u2013, U+2013) in:\n"
            + "\n".join(violations)
        )
