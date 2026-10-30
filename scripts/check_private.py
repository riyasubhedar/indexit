"""Privacy check: blocks a commit that would publish personal data. Runs before every commit.

  python3 scripts/check_private.py          # check what's staged (the pre-commit hook runs this)
  python3 scripts/check_private.py --all    # check every file git would publish

Blocks: anything under data/ (settings incl. the SEC contact email, conversations, filings, index), PDFs,
files over 5 MB, email addresses (except no-reply ones), home-folder paths, API keys or tokens, and the
words in .private-terms (one per line; a local, never-committed list of personal details).
Findings are shown masked, so the check itself never prints what it found.
Plain Python 3 standard library, so it runs with the Mac's built-in python3.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
SELF = "scripts/check_private.py"
TERMS_FILE = Path(".private-terms")
ALLOWED_EMAIL = re.compile(r"@(users\.noreply\.github\.com|example\.(com|org)|anthropic\.com)$", re.I)
PATTERNS = {
    "email address": re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"),
    "home-folder path": re.compile(r"/(Users|home)/[^/\s\"'`]+/"),
    "API key or token": re.compile(
        r"sk-ant-[\w-]{10,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16}"
        r"|xox[abprs]-[\w-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    ),
}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _mask(text: str) -> str:
    return text[:2] + "…" + text[-2:] if len(text) > 6 else "…"


def _path_problem(path: str) -> str | None:
    if path.startswith("data/"):
        return "personal data folder (data/)"
    if path.lower().endswith(".pdf"):
        return "PDF file"
    file = Path(path)
    if file.exists() and file.stat().st_size > MAX_BYTES:
        return "file over 5 MB"
    return None


def _private_terms() -> re.Pattern | None:
    terms = [t.strip() for t in TERMS_FILE.read_text().splitlines()] if TERMS_FILE.exists() else []
    terms = [t for t in terms if t and not t.startswith("#")]
    return re.compile("|".join(re.escape(t) for t in terms), re.I) if terms else None


PRIVATE = _private_terms()


def _line_problems(path: str, number: int, line: str) -> list[str]:
    found = []
    if PRIVATE:
        found += [f"{path}:{number}: personal term ({_mask(m.group())})" for m in PRIVATE.finditer(line)]
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(line):
            if kind == "email address" and ALLOWED_EMAIL.search(match.group()):
                continue
            found.append(f"{path}:{number}: {kind} ({_mask(match.group())})")
    return found


def staged() -> list[tuple[str, list[tuple[int, str]]]]:
    """Staged files with their added lines (line number, text)."""
    files = [p for p in _git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines() if p]
    result = []
    for path in files:
        added, number = [], 0
        for line in _git("diff", "--cached", "-U0", "--", path).splitlines():
            hunk = re.match(r"@@ -\S+ \+(\d+)", line)
            if hunk:
                number = int(hunk.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                added.append((number, line[1:]))
                number += 1
        result.append((path, added))
    return result


def everything() -> list[tuple[str, list[tuple[int, str]]]]:
    """Every file git would publish: tracked plus untracked-but-not-ignored."""
    files = set(_git("ls-files").splitlines()) | set(_git("ls-files", "--others", "--exclude-standard").splitlines())
    result = []
    for path in sorted(p for p in files if p):
        try:
            lines = Path(path).read_text(errors="replace").splitlines()
        except (IsADirectoryError, FileNotFoundError):
            continue
        result.append((path, list(enumerate(lines, 1))))
    return result


def main() -> int:
    problems = []
    for path, lines in everything() if "--all" in sys.argv else staged():
        if path == SELF:
            continue
        problem = _path_problem(path)
        if problem:
            problems.append(f"{path}: {problem}")
            continue
        for number, line in lines:
            problems += _line_problems(path, number, line)
    if problems:
        print("Privacy check failed: these would be published:\n  " + "\n  ".join(problems), file=sys.stderr)
        print("Remove or redact them (or add the file to .gitignore), then commit again.", file=sys.stderr)
        return 1
    print("Privacy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
