"""Git helpers, all via subprocess calling the git binary.

Every failure becomes a ShipkitError with the git output included,
never a raw CalledProcessError traceback.
"""

import subprocess
from pathlib import Path

from shipkit.core.errors import ShipkitError


def run_git(repo: Path, *args: str) -> str:
    """Run a git command in `repo` and return stdout (stripped)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as err:
        raise ShipkitError("git executable not found on PATH") from err
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ShipkitError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def repo_root(start: Path) -> Path:
    """Return the top-level directory of the git repo containing `start`."""
    if not Path(start).exists():
        raise ShipkitError(f"Path does not exist: {start}")
    try:
        top = run_git(Path(start), "rev-parse", "--show-toplevel")
    except ShipkitError as err:
        raise ShipkitError(f"{start} is not inside a git repository") from err
    return Path(top)


def changed_files(repo: Path, base: str) -> list[str]:
    """Files changed between `base` and HEAD: git diff --name-only base...HEAD."""
    root = repo_root(repo)
    try:
        run_git(root, "rev-parse", "--verify", "--quiet", base)
    except ShipkitError as err:
        raise ShipkitError(
            f"Base ref '{base}' not found in this repository. "
            "Fetch it or pass a different --base."
        ) from err
    output = run_git(root, "diff", "--name-only", f"{base}...HEAD")
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def latest_tag(repo: Path) -> str | None:
    """The most recent version tag (v*), or None if the repo has none."""
    output = run_git(repo, "tag", "--list", "v*", "--sort=-v:refname")
    if not output:
        return None
    return output.splitlines()[0].strip()


def commits_since(repo: Path, tag: str | None) -> list[tuple[str, str]]:
    """(subject, body) for every commit since `tag` (or all commits)."""
    range_spec = f"{tag}..HEAD" if tag else "HEAD"
    try:
        output = run_git(
            repo, "log", range_spec, "--format=%s%x00%b%x1e", "--no-merges"
        )
    except ShipkitError:
        return []  # a repo with no commits yet
    commits: list[tuple[str, str]] = []
    for record in output.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        subject, _, body = record.partition("\x00")
        commits.append((subject.strip(), body.strip()))
    return commits


def remote_repo_slug(repo: Path) -> str | None:
    """owner/repo parsed from the origin remote URL, if there is one."""
    try:
        url = run_git(repo, "remote", "get-url", "origin")
    except ShipkitError:
        return None
    cleaned = url.removesuffix(".git").rstrip("/")
    for sep in ("github.com:", "github.com/"):
        if sep in cleaned:
            return cleaned.split(sep, 1)[1]
    return None
