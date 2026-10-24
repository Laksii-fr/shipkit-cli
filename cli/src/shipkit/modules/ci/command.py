"""`shipkit ci` command. Thin: parse flags, call the controller, report."""

from pathlib import Path
from typing import Annotated

import typer

from shipkit.core.console import print_error
from shipkit.core.errors import ShipkitError
from shipkit.modules.ci import controller, report


def _resolve_config(config: Path, repo: Path) -> Path:
    """Prefer repo/config, then cwd/config, so nested monorepos stay ergonomic."""
    if config.is_absolute():
        return config
    under_repo = (repo / config).resolve()
    if under_repo.is_file():
        return under_repo
    under_cwd = (Path.cwd() / config).resolve()
    if under_cwd.is_file():
        return under_cwd
    return under_repo


def register(app: typer.Typer) -> None:
    @app.command("ci")
    def ci_command(
        base: Annotated[str, typer.Option("--base", help="Git ref to diff against.")] = "main",
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Print the plan, run nothing.")
        ] = False,
        run_all: Annotated[
            bool, typer.Option("--all", help="Run every service, ignore the diff.")
        ] = False,
        max_workers: Annotated[
            int, typer.Option("--max-workers", help="Parallel services per layer.")
        ] = 4,
        config: Annotated[
            Path, typer.Option("--config", help="Path to shipkit.yml.")
        ] = Path("shipkit.yml"),
        repo: Annotated[Path, typer.Option("--repo", help="Repo to run in.")] = Path("."),
    ) -> None:
        """Run build/test only for services affected by a change."""
        try:
            result = controller.run_ci(
                repo=repo,
                config_path=_resolve_config(config, repo),
                base=base,
                run_all=run_all,
                dry_run=dry_run,
                max_workers=max_workers,
            )
        except ShipkitError as err:
            print_error(str(err))
            raise typer.Exit(code=1) from err
        report.print_report(result)
        report.write_step_summary(result)
        if not result.success:
            raise typer.Exit(code=1)
