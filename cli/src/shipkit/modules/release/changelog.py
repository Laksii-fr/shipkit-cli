"""Building and prepending CHANGELOG.md sections."""

from shipkit.modules.release.models import ParsedCommit

_GROUPS: list[tuple[str, object]] = [
    ("Breaking Changes", lambda c: c.breaking),
    ("Features", lambda c: c.type == "feat" and not c.breaking),
    ("Fixes", lambda c: c.type == "fix" and not c.breaking),
]
_OTHER = "Other Changes"


def _line(commit: ParsedCommit) -> str:
    scope = f"**{commit.scope}:** " if commit.scope else ""
    return f"- {scope}{commit.description}"


def render_section(version: str, date: str, commits: list[ParsedCommit]) -> str:
    """Render one release section, commits grouped by kind."""
    lines = [f"## v{version} - {date}", ""]
    placed: set[int] = set()
    for title, matches in _GROUPS:
        group = [c for i, c in enumerate(commits) if matches(c) and i not in placed]
        placed.update(i for i, c in enumerate(commits) if matches(c))
        if group:
            lines.append(f"### {title}")
            lines.extend(_line(c) for c in group)
            lines.append("")
    rest = [c for i, c in enumerate(commits) if i not in placed]
    if rest:
        lines.append(f"### {_OTHER}")
        lines.extend(_line(c) for c in rest)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def prepend_changelog(existing: str, section: str) -> str:
    """Return the new CHANGELOG content with `section` at the top.

    An existing '# Changelog' title is kept as the first line, and all
    previous sections are preserved below the new one.
    """
    if not existing.strip():
        return f"# Changelog\n\n{section}"
    if existing.startswith("# Changelog"):
        first_newline = existing.find("\n")
        header = existing[:first_newline]
        rest = existing[first_newline + 1 :].lstrip("\n")
        return f"{header}\n\n{section}\n{rest}"
    return f"{section}\n{existing}"
