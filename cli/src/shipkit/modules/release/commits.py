"""Parsing Conventional Commits: https://www.conventionalcommits.org

    feat(api): add export
    fix!: drop python 3.10
    feat: new thing

    BREAKING CHANGE: the config format changed
"""

import re

from shipkit.modules.release.models import ParsedCommit

_PATTERN = re.compile(
    r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s+(?P<description>.+)$"
)
_BREAKING_FOOTERS = ("BREAKING CHANGE:", "BREAKING-CHANGE:")


def parse_commit(subject: str, body: str = "") -> ParsedCommit | None:
    """Parse one commit, or return None if it is not conventional."""
    match = _PATTERN.match(subject.strip())
    if not match:
        return None
    breaking = bool(match.group("bang")) or any(
        line.strip().startswith(_BREAKING_FOOTERS) for line in body.splitlines()
    )
    return ParsedCommit(
        type=match.group("type").lower(),
        scope=match.group("scope") or None,
        breaking=breaking,
        description=match.group("description").strip(),
        raw_subject=subject.strip(),
    )


def parse_commits(raw: list[tuple[str, str]]) -> tuple[list[ParsedCommit], int]:
    """Parse (subject, body) pairs. Returns (parsed, ignored_count)."""
    parsed: list[ParsedCommit] = []
    ignored = 0
    for subject, body in raw:
        commit = parse_commit(subject, body)
        if commit is None:
            ignored += 1
        else:
            parsed.append(commit)
    return parsed, ignored


def decide_bump(commits: list[ParsedCommit]) -> str:
    """major if any breaking, else minor if any feat, else patch."""
    if any(commit.breaking for commit in commits):
        return "major"
    if any(commit.type == "feat" for commit in commits):
        return "minor"
    return "patch"
