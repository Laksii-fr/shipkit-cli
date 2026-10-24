"""Release orchestration.

plan_release() inspects a real git repo and computes the plan.
execute_release() applies it. Dry-run means: plan only, zero writes,
zero git changes. Push and GitHub release happen only when the
caller explicitly asks for them, so local runs are always safe.
"""

import os
from datetime import date
from pathlib import Path

from shipkit.core import git
from shipkit.core.config import load_config
from shipkit.core.errors import ShipkitError
from shipkit.modules.release import github_client
from shipkit.modules.release.changelog import prepend_changelog, render_section
from shipkit.modules.release.commits import decide_bump, parse_commits
from shipkit.modules.release.models import ReleasePlan, ReleaseResult
from shipkit.modules.release.version import SemVer


def _current_version(repo: Path, version_file: str, tag: str | None) -> SemVer:
    if tag:
        return SemVer.parse(tag)
    version_path = repo / version_file
    if version_path.is_file():
        return SemVer.parse(version_path.read_text(encoding="utf-8").strip())
    return SemVer(0, 0, 0)


def plan_release(*, repo: Path, config_path: Path) -> ReleasePlan:
    config = load_config(config_path)
    root = git.repo_root(repo)
    tag = git.latest_tag(root)
    raw_commits = git.commits_since(root, tag)
    if not raw_commits:
        since = f" since {tag}" if tag else ""
        raise ShipkitError(f"No commits{since}, nothing to release.")
    commits, ignored = parse_commits(raw_commits)
    if not commits and not tag:
        pass  # first release of only non-conventional commits: patch bump
    elif not commits:
        raise ShipkitError(
            f"No Conventional Commits since {tag}, nothing releasable. "
            "Use messages like 'feat: ...' or 'fix: ...'."
        )
    bump = decide_bump(commits) if commits else "patch"
    current = _current_version(root, config.release.version_file, tag)
    nxt = current.bump(bump)
    return ReleasePlan(
        current_version=str(current),
        next_version=str(nxt),
        bump=bump,
        tag=f"v{nxt}",
        commits=commits,
        ignored_commits=ignored,
    )


def execute_release(
    *,
    repo: Path,
    config_path: Path,
    dry_run: bool = False,
    push: bool = False,
    github: bool = False,
    token: str | None = None,
    http_client=None,
    today: date | None = None,
) -> ReleaseResult:
    config = load_config(config_path)
    root = git.repo_root(repo)
    plan = plan_release(repo=repo, config_path=config_path)
    section = render_section(
        plan.next_version, (today or date.today()).isoformat(), plan.commits
    )
    if dry_run:
        return ReleaseResult(plan=plan, dry_run=True, changelog_section=section)

    version_path = root / config.release.version_file
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text(f"{plan.next_version}\n", encoding="utf-8")

    changelog_path = root / "CHANGELOG.md"
    existing = changelog_path.read_text(encoding="utf-8") if changelog_path.is_file() else ""
    changelog_path.write_text(prepend_changelog(existing, section), encoding="utf-8")

    git.run_git(root, "add", config.release.version_file, "CHANGELOG.md")
    git.run_git(root, "commit", "-m", f"chore(release): {plan.tag}")
    git.run_git(root, "tag", plan.tag)

    # Validate GitHub prerequisites before any network push so failures
    # are clear (missing token / repo) instead of a confusing remote error.
    release_url: str | None = None
    auth: str | None = None
    owner = repo_name = ""
    if github:
        slug = config.release.github_repo or git.remote_repo_slug(root)
        if not slug or "/" not in slug:
            raise ShipkitError(
                "Cannot create a GitHub release: no owner/repo known. "
                "Set release.github_repo in shipkit.yml or add an origin remote."
            )
        owner, repo_name = slug.split("/", 1)
        auth = token or os.environ.get("GITHUB_TOKEN")
        if not auth:
            raise ShipkitError(
                "Cannot create a GitHub release: GITHUB_TOKEN is not set."
            )

    pushed = False
    if push or github:
        git.run_git(root, "push", "origin", "HEAD")
        git.run_git(root, "push", "origin", plan.tag)
        pushed = True

    if github:
        assert auth is not None  # checked above
        release_url = github_client.create_release(
            owner=owner,
            repo=repo_name,
            tag=plan.tag,
            name=plan.tag,
            body=section,
            token=auth,
            client=http_client,
        )
    return ReleaseResult(
        plan=plan,
        dry_run=False,
        changelog_section=section,
        pushed=pushed,
        github_release_url=release_url,
    )
