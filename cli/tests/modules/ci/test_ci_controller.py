"""Phase 2: CI controller on real temp git repos with a fake runner."""

import subprocess
from pathlib import Path

from shipkit.modules.ci.models import ServiceRunResult

GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com"]

YML = """
services:
  common:
    path: libs/common
    test: "pytest -q"
  api:
    path: services/api
    depends_on: [common]
    test: "pytest -q"
  worker:
    path: services/worker
    depends_on: [common]
    test: "pytest -q"
"""


def git(repo: Path, *args: str) -> None:
    subprocess.run([*GIT, *args], cwd=repo, check=True, capture_output=True)


class RecordingRunner:
    def __init__(self, fail: set[str] | None = None) -> None:
        self.ran: list[str] = []
        self.fail = fail or set()

    def run_service(self, service, repo_root):
        self.ran.append(service.name)
        status = "failed" if service.name in self.fail else "passed"
        return ServiceRunResult(service=service.name, status=status, duration_seconds=0.01)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for sub in ("libs/common", "services/api", "services/worker"):
        (repo / sub).mkdir(parents=True)
        (repo / sub / "code.py").write_text("x = 1\n")
    (repo / "shipkit.yml").write_text(YML)
    git(repo, "init", "-b", "main")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "feat: init")
    return repo


def change_and_commit(repo: Path, rel: str, content: str) -> None:
    git(repo, "checkout", "-b", "feature")
    (repo / rel).write_text(content)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fix: change")


def test_controller_runs_only_affected_service(tmp_path):
    from shipkit.modules.ci.controller import run_ci

    repo = make_repo(tmp_path)
    change_and_commit(repo, "services/api/code.py", "x = 2\n")
    runner = RecordingRunner()
    result = run_ci(repo=repo, config_path=repo / "shipkit.yml", base="main", runner=runner)
    assert runner.ran == ["api"]
    assert result.success is True


def test_controller_common_change_runs_dependents_in_layers(tmp_path):
    from shipkit.modules.ci.controller import run_ci

    repo = make_repo(tmp_path)
    change_and_commit(repo, "libs/common/code.py", "x = 2\n")
    runner = RecordingRunner()
    result = run_ci(repo=repo, config_path=repo / "shipkit.yml", base="main", runner=runner)
    assert result.plan.layers == [["common"], ["api", "worker"]]
    assert runner.ran[0] == "common"
    assert set(runner.ran[1:]) == {"api", "worker"}


def test_controller_dry_run_plans_without_running(tmp_path):
    from shipkit.modules.ci.controller import run_ci

    repo = make_repo(tmp_path)
    change_and_commit(repo, "libs/common/code.py", "x = 2\n")
    runner = RecordingRunner()
    result = run_ci(
        repo=repo, config_path=repo / "shipkit.yml", base="main", dry_run=True, runner=runner
    )
    assert runner.ran == []
    assert all(r.status == "planned" for r in result.results)
    assert len(result.results) == 3


def test_controller_failure_stops_later_layers_and_fails(tmp_path):
    from shipkit.modules.ci.controller import run_ci

    repo = make_repo(tmp_path)
    change_and_commit(repo, "libs/common/code.py", "x = 2\n")
    runner = RecordingRunner(fail={"common"})
    result = run_ci(repo=repo, config_path=repo / "shipkit.yml", base="main", runner=runner)
    assert runner.ran == ["common"]
    assert result.success is False
    assert result.exit_code == 1


def test_controller_run_all_ignores_diff(tmp_path):
    from shipkit.modules.ci.controller import run_ci

    repo = make_repo(tmp_path)
    runner = RecordingRunner()
    result = run_ci(
        repo=repo, config_path=repo / "shipkit.yml", run_all=True, runner=runner
    )
    assert set(runner.ran) == {"common", "api", "worker"}
    assert result.success is True


def test_controller_no_changes_runs_nothing(tmp_path):
    from shipkit.modules.ci.controller import run_ci

    repo = make_repo(tmp_path)
    runner = RecordingRunner()
    result = run_ci(repo=repo, config_path=repo / "shipkit.yml", base="HEAD", runner=runner)
    assert runner.ran == []
    assert result.results == []


def test_controller_nested_monorepo_strips_git_prefix(tmp_path):
    """shipkit.yml in a subdirectory of a larger git repo."""
    from shipkit.modules.ci.controller import run_ci

    git_root = tmp_path / "super"
    mono = git_root / "examples" / "monorepo"
    for sub in ("libs/common", "services/api", "services/worker"):
        (mono / sub).mkdir(parents=True)
        (mono / sub / "code.py").write_text("x = 1\n")
    (mono / "shipkit.yml").write_text(YML)
    (git_root / "README.md").write_text("super\n")
    git(git_root, "init", "-b", "main")
    git(git_root, "add", ".")
    git(git_root, "commit", "-m", "feat: init")
    git(git_root, "checkout", "-b", "feature")
    (mono / "services" / "api" / "code.py").write_text("x = 2\n")
    git(git_root, "add", ".")
    git(git_root, "commit", "-m", "fix: api")

    runner = RecordingRunner()
    result = run_ci(
        repo=mono,
        config_path=mono / "shipkit.yml",
        base="main",
        runner=runner,
    )
    assert runner.ran == ["api"]
    assert result.success is True


def test_files_relative_to_monorepo_helper():
    from shipkit.modules.ci.controller import files_relative_to_monorepo

    git_root = Path("/repo")
    mono = Path("/repo/examples/monorepo")
    files = [
        "examples/monorepo/services/api/x.py",
        "README.md",
        "cli/src/x.py",
    ]
    assert files_relative_to_monorepo(git_root, mono, files) == ["services/api/x.py"]
