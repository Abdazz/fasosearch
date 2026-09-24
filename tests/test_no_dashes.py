"""Guard test: no em dash (U+2014) or en dash (U+2013) in git-tracked source code."""

import subprocess
import sys
from pathlib import Path

import pytest


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

    # Exclusions
    excluded_dirs = {"data", "node_modules"}
    excluded_suffixes = {".xlsx"}
    excluded_files = {"package-lock.json"}

    violations = []

    for file_path_str in git_files:
        file_path = repo_root / file_path_str
        parts = file_path.parts

        # Skip excluded directories
        if any(part in excluded_dirs for part in parts):
            continue

        # Skip excluded file patterns
        if file_path.name in excluded_files or file_path.suffix in excluded_suffixes:
            continue

        # Try to read file as UTF-8
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            # Ignore binary files and missing files
            continue

        # Check for em dash (U+2014) and en dash (U+2013)
        for line_num, line in enumerate(content.split("\n"), start=1):
            if "\u2014" in line or "\u2013" in line:
                violations.append(f"{file_path_str}:{line_num}")

    if violations:
        pytest.fail(
            "Found em dash (\\u2014, U+2014) or en dash (\\u2013, U+2013) in:\n"
            + "\n".join(violations)
        )
