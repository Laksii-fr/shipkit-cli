"""`shipkit release` command. Thin: parse flags, call controller, show plan."""

from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from shipkit.core.console import console, print_error
from shipkit.core.errors import ShipkitError
from shipkit.modules.release import controller


def _show_plan(result) -> None:
    plan = result.plan
    table = Table(title="Release plan" if result.dry_run else "Release done")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Current version", plan.current_version)
    table.add_row("Next version", plan.next_version)
    table.add_row("Bump", plan.bump)
    table.add_row("Tag", plan.tag)
    table.add_row("Conventional commits", str(len(plan.commits)))
    table.add_row("Ignored commits", str(plan.ignored_commits))
    console.print(table)
    console.print(Panel(result.changelog_section.strip(), title="CHANGELOG section"))
    if result.github_release_url:
        console.print(f"[green]GitHub release:[/green] {result.github_release_url}")


def register(app: typer.Typer) -> None:
    @app.command("release")
    def release_command(
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Print the plan, change nothing.")
        ] = False,
        push: Annotated[
            bool, typer.Option("--push", help="Push the commit and tag to origin.")
        ] = False,
        github: Annotated[
            bool, typer.Option("--github", help="Also create a GitHub release.")
        ] = False,
        config: Annotated[
            Path, typer.Option("--config", help="Path to shipkit.yml.")
        ] = Path("shipkit.yml"),
        repo: Annotated[Path, typer.Option("--repo", help="Repo to release.")] = Path("."),
    ) -> None:
        """Bump the version from Conventional Commits and tag a release."""
        try:
            result = controller.execute_release(
                repo=repo,
                config_path=config if config.is_absolute() else repo / config,
                dry_run=dry_run,
                push=push,
                github=github,
            )
        except ShipkitError as err:
            print_error(str(err))
            raise typer.Exit(code=1) from err
        _show_plan(result)
