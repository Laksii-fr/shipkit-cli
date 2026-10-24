"""Phase 1: git helpers against real temporary git repos."""

import subprocess
from pathlib import Path

import pytest

from shipkit.core.errors import ShipkitError
from shipkit.core.git import changed_files, commits_since, latest_tag, repo_root

GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com"]


def git(repo: Path, *args: str) -> None:
    subprocess.run([*GIT, *args], cwd=repo, check=True, capture_output=True)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    (repo / "a.txt").write_text("one\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "feat: initial")
    return repo


def test_repo_root(tmp_path):
    repo = make_repo(tmp_path)
    assert repo_root(repo) == repo.resolve()


def test_repo_root_rejects_non_repo(tmp_path):
    with pytest.raises(ShipkitError, match="not inside a git repository"):
        repo_root(tmp_path)


def test_changed_files_between_base_and_head(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "b.txt").write_text("two\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fix: add b")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD~1"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    assert changed_files(repo, base) == ["b.txt"]


def test_changed_files_unknown_base_is_clear_error(tmp_path):
    repo = make_repo(tmp_path)
    with pytest.raises(ShipkitError, match="Base ref 'nope' not found"):
        changed_files(repo, "nope")


def test_changed_files_no_changes(tmp_path):
    repo = make_repo(tmp_path)
    assert changed_files(repo, "HEAD") == []


def test_latest_tag_and_commits_since(tmp_path):
    repo = make_repo(tmp_path)
    git(repo, "tag", "v1.2.3")
    (repo / "c.txt").write_text("three\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "feat: add c")
    assert latest_tag(repo) == "v1.2.3"
    commits = commits_since(repo, "v1.2.3")
    assert [subject for subject, _ in commits] == ["feat: add c"]


def test_latest_tag_none_when_no_tags(tmp_path):
    repo = make_repo(tmp_path)
    assert latest_tag(repo) is None
    assert len(commits_since(repo, None)) == 1
