"""CI orchestration: config + diff -> plan -> run layers in parallel.

All logic lives here so it can be tested without Typer or Docker:
the runner is injected, and a fake runner stands in for Docker
in tests.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Protocol

from shipkit.core.config import load_config
from shipkit.core.git import changed_files, repo_root
from shipkit.modules.ci.affected import build_plan, plan_for_all
from shipkit.modules.ci.models import CiResult, ServiceRunResult


class RunnerProtocol(Protocol):
    def run_service(self, service, repo_root: Path) -> ServiceRunResult: ...


def _monorepo_root(repo: Path, config_path: Path) -> Path:
    """Directory that service paths in shipkit.yml are relative to."""
    resolved = Path(repo).resolve()
    if resolved.is_dir():
        return resolved
    return Path(config_path).resolve().parent


def files_relative_to_monorepo(git_root: Path, monorepo: Path, files: list[str]) -> list[str]:
    """Map git-root-relative paths to monorepo-relative paths.

    When shipkit.yml lives in a subdirectory of a larger git repo
    (e.g. examples/monorepo), git diff returns paths like
    ``examples/monorepo/services/api/x.py``. Service paths in the
    config are ``services/api``, so we strip the monorepo prefix and
    ignore files outside it.
    """
    git_root = git_root.resolve()
    monorepo = monorepo.resolve()
    try:
        prefix = monorepo.relative_to(git_root).as_posix()
    except ValueError:
        return files
    if prefix in ("", "."):
        return files
    relative: list[str] = []
    for path in files:
        normalised = path.replace("\\", "/")
        if normalised == prefix:
            continue
        if normalised.startswith(prefix + "/"):
            relative.append(normalised[len(prefix) + 1 :])
    return relative


def run_ci(
    *,
    repo: Path,
    config_path: Path,
    base: str = "main",
    run_all: bool = False,
    dry_run: bool = False,
    max_workers: int = 4,
    runner: RunnerProtocol | None = None,
) -> CiResult:
    """Run change-aware CI for the repo at `repo`."""
    config = load_config(config_path)
    work_root = _monorepo_root(repo, config_path)

    if run_all:
        plan = plan_for_all(config)
    else:
        git_top = repo_root(repo)
        files = changed_files(git_top, base)
        files = files_relative_to_monorepo(git_top, work_root, files)
        plan = build_plan(config, files)

    if not plan.affected:
        return CiResult(plan=plan, results=[], dry_run=dry_run)

    if dry_run:
        results = [
            ServiceRunResult(service=name, status="planned")
            for layer in plan.layers
            for name in layer
        ]
        return CiResult(plan=plan, results=results, dry_run=True)

    if runner is None:
        from shipkit.modules.ci.runner import DockerRunner

        runner = DockerRunner()

    results: list[ServiceRunResult] = []
    for layer in plan.layers:
        workers = max(1, min(max_workers, len(layer)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            layer_results = list(
                pool.map(
                    lambda name: runner.run_service(config.services[name], work_root),
                    layer,
                )
            )
        results.extend(layer_results)
        if any(result.status == "failed" for result in layer_results):
            break  # later layers depend on this one; stop here
    return CiResult(plan=plan, results=results, dry_run=False)
