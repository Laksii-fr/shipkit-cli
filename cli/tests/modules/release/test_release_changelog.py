"""Phase 4: changelog grouping and prepending."""

from shipkit.modules.release.changelog import prepend_changelog, render_section
from shipkit.modules.release.commits import parse_commits


def parsed(*subjects):
    commits, _ = parse_commits([(s, "") for s in subjects])
    return commits


def test_section_groups_commits():
    section = render_section(
        "1.5.0",
        "2026-10-24",
        parsed("feat(api): add export", "fix: stop crash", "feat!: drop old api", "docs: typo"),
    )
    assert "## v1.5.0 - 2026-10-24" in section
    assert "### Breaking Changes" in section
    assert "### Features" in section
    assert "### Fixes" in section
    assert "### Other Changes" in section
    breaking_at = section.index("### Breaking Changes")
    features_at = section.index("### Features")
    assert breaking_at < features_at
    assert "- **api:** add export" in section


def test_prepend_keeps_header_and_history():
    existing = "# Changelog\n\n## v1.0.0 - 2026-01-01\n\n- old thing\n"
    section = render_section("1.1.0", "2026-02-01", parsed("feat: new"))
    combined = prepend_changelog(existing, section)
    assert combined.startswith("# Changelog")
    assert combined.index("v1.1.0") < combined.index("v1.0.0")
    assert "old thing" in combined


def test_prepend_creates_file_content_when_empty():
    section = render_section("0.1.0", "2026-01-01", parsed("feat: first"))
    combined = prepend_changelog("", section)
    assert combined.startswith("# Changelog")
    assert "v0.1.0" in combined
