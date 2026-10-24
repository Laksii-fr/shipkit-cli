"""Data models for the release feature."""

from pydantic import BaseModel, Field


class ParsedCommit(BaseModel):
    """One commit, parsed as a Conventional Commit."""

    type: str
    scope: str | None = None
    breaking: bool = False
    description: str
    raw_subject: str


class ReleasePlan(BaseModel):
    """What a release will do, computed before anything changes."""

    current_version: str
    next_version: str
    bump: str  # major | minor | patch
    tag: str
    commits: list[ParsedCommit] = Field(default_factory=list)
    ignored_commits: int = 0


class ReleaseResult(BaseModel):
    """What a release did (or, for dry-run, would do)."""

    plan: ReleasePlan
    dry_run: bool
    changelog_section: str
    pushed: bool = False
    github_release_url: str | None = None
