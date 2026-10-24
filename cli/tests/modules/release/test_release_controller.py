"""Phase 4: release controller on real temp git repos + GitHub client."""

import subprocess
from pathlib import Path

import httpx
import pytest

from shipkit.core import git
from shipkit.core.errors import ShipkitError
from shipkit.modules.release import github_client
from shipkit.modules.release.controller import execute_release, plan_release

YML = """
services:
  app:
    path: app
release:
  version_file: VERSION
"""


def git_cmd(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "code.py").write_text("x = 1\n")
    (repo / "shipkit.yml").write_text(YML)
    (repo / "VERSION").write_text("1.4.2\n")
    git_cmd(repo, "init", "-b", "main")
    # Repo-local identity (never global) so the release commit can be made.
    git_cmd(repo, "config", "user.name", "Test")
    git_cmd(repo, "config", "user.email", "test@example.com")
    git_cmd(repo, "add", ".")
    git_cmd(repo, "commit", "-m", "feat: initial")
    git_cmd(repo, "tag", "v1.4.2")
    return repo


def add_commit(repo: Path, message: str, filename: str = "app/code.py") -> None:
    path = repo / filename
    existing = path.read_text() if path.exists() else ""
    path.write_text(existing + "# change\n")
    git_cmd(repo, "add", ".")
    git_cmd(repo, "commit", "-m", message)


def test_plan_minor_bump_from_feat(tmp_path):
    repo = make_repo(tmp_path)
    add_commit(repo, "feat: add export")
    add_commit(repo, "fix: a bug", "app/other.py")
    plan = plan_release(repo=repo, config_path=repo / "shipkit.yml")
    assert plan.current_version == "1.4.2"
    assert plan.next_version == "1.5.0"
    assert plan.bump == "minor"
    assert plan.tag == "v1.5.0"
    assert len(plan.commits) == 2


def test_plan_major_bump_from_breaking(tmp_path):
    repo = make_repo(tmp_path)
    add_commit(repo, "feat!: new api")
    plan = plan_release(repo=repo, config_path=repo / "shipkit.yml")
    assert plan.next_version == "2.0.0"


def test_plan_no_new_commits_errors(tmp_path):
    repo = make_repo(tmp_path)
    with pytest.raises(ShipkitError, match="nothing to release"):
        plan_release(repo=repo, config_path=repo / "shipkit.yml")


def test_dry_run_changes_nothing(tmp_path):
    repo = make_repo(tmp_path)
    add_commit(repo, "feat: shiny")
    version_before = (repo / "VERSION").read_text()
    tags_before = git.latest_tag(repo)
    result = execute_release(repo=repo, config_path=repo / "shipkit.yml", dry_run=True)
    assert result.dry_run is True
    assert (repo / "VERSION").read_text() == version_before
    assert not (repo / "CHANGELOG.md").exists()
    assert git.latest_tag(repo) == tags_before


def test_full_local_release_updates_version_changelog_and_tag(tmp_path):
    repo = make_repo(tmp_path)
    add_commit(repo, "feat: shiny thing")
    add_commit(repo, "fix: broken thing", "app/other.py")
    result = execute_release(repo=repo, config_path=repo / "shipkit.yml")
    assert result.dry_run is False
    assert (repo / "VERSION").read_text().strip() == "1.5.0"
    changelog = (repo / "CHANGELOG.md").read_text()
    assert "## v1.5.0" in changelog
    assert "shiny thing" in changelog
    assert git.latest_tag(repo) == "v1.5.0"
    log = git.commits_since(repo, "v1.4.2")
    subjects = [s for s, _ in log]
    assert "feat: shiny thing" in subjects
    assert "chore(release): v1.5.0" in subjects


def test_github_client_posts_release_with_mock_transport():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(201, json={"html_url": "https://github.com/o/r/releases/v1"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    url = github_client.create_release(
        owner="o", repo="r", tag="v1.5.0", name="v1.5.0", body="notes",
        token="secret-token", client=client,
    )
    assert url == "https://github.com/o/r/releases/v1"
    assert seen["url"] == "https://api.github.com/repos/o/r/releases"
    assert seen["auth"] == "Bearer secret-token"


def test_github_client_http_error_is_clear():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="validation failed")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ShipkitError, match="HTTP 422"):
        github_client.create_release(
            owner="o", repo="r", tag="v1", name="v1", body="b", token="t", client=client
        )
