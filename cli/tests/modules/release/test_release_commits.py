"""Phase 4: Conventional Commit parsing and bump decisions."""

import pytest

from shipkit.modules.release.commits import decide_bump, parse_commit, parse_commits


@pytest.mark.parametrize(
    "subject,expected_type,scope,breaking",
    [
        ("feat: add export", "feat", None, False),
        ("feat(api): add export", "feat", "api", False),
        ("fix(parser): handle empty file", "fix", "parser", False),
        ("feat!: drop python 3.10", "feat", None, True),
        ("fix(core)!: change config format", "fix", "core", True),
        ("docs: update readme", "docs", None, False),
        ("chore(release): v1.2.0", "chore", "release", False),
    ],
)
def test_parse_conventional(subject, expected_type, scope, breaking):
    commit = parse_commit(subject)
    assert commit is not None
    assert commit.type == expected_type
    assert commit.scope == scope
    assert commit.breaking is breaking


def test_breaking_change_footer():
    commit = parse_commit("feat: new config", "Some body.\n\nBREAKING CHANGE: format changed")
    assert commit is not None
    assert commit.breaking is True


def test_breaking_change_hyphen_footer():
    commit = parse_commit("refactor: redo", "BREAKING-CHANGE: api removed")
    assert commit is not None
    assert commit.breaking is True


@pytest.mark.parametrize("subject", ["random work", "update stuff", "WIP", ""])
def test_non_conventional_is_ignored(subject):
    assert parse_commit(subject) is None


def test_parse_commits_counts_ignored():
    parsed, ignored = parse_commits([("feat: a", ""), ("random", ""), ("fix: b", "")])
    assert len(parsed) == 2
    assert ignored == 1


def test_bump_matrix():
    def commits(*subjects):
        parsed, _ = parse_commits([(s, "") for s in subjects])
        return parsed

    assert decide_bump(commits("fix!: x")) == "major"
    assert decide_bump(commits("feat: x", "fix: y")) == "minor"
    assert decide_bump(commits("fix: x")) == "patch"
    assert decide_bump(commits("docs: x", "chore: y")) == "patch"
    assert decide_bump([]) == "patch"
