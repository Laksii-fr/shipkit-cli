"""`shipkit run` and `shipkit logs` commands. Thin wrappers."""

import os
from typing import Annotated

import typer
from rich.table import Table

from shipkit.core.console import console, print_error
from shipkit.core.errors import ShipkitError
from shipkit.modules.logs import controller
from shipkit.modules.logs.client import LogClient

_DEFAULT_COLLECTOR = "http://localhost:8000"


def _collector_url(option: str | None) -> str:
    return option or os.environ.get("SHIPKIT_COLLECTOR_URL") or _DEFAULT_COLLECTOR


def register(app: typer.Typer) -> None:
    @app.command("run")
    def run_command(
        service: Annotated[str, typer.Argument(help="Service name for the logs.")],
        image: Annotated[str, typer.Argument(help="Docker image to run.")],
        collector: Annotated[
            str | None, typer.Option("--collector", help="Collector URL.")
        ] = None,
    ) -> None:
        """Run a container and ship its logs to the collector."""
        try:
            shipped = controller.run_container(
                service=service, image=image, collector_url=_collector_url(collector)
            )
        except ShipkitError as err:
            print_error(str(err))
            raise typer.Exit(code=1) from err
        console.print(f"[green]Shipped {shipped} log lines for '{service}'.[/green]")

    @app.command("logs")
    def logs_command(
        service: Annotated[
            str | None, typer.Option("--service", help="Filter by service.")
        ] = None,
        level: Annotated[
            str | None, typer.Option("--level", help="Filter by level.")
        ] = None,
        since: Annotated[
            str | None, typer.Option("--since", help="Only newer than e.g. 30m, 1h, 2d.")
        ] = None,
        grep: Annotated[
            str | None, typer.Option("--grep", help="Text to search for.")
        ] = None,
        limit: Annotated[int, typer.Option("--limit", help="Max lines to show.")] = 200,
        collector: Annotated[
            str | None, typer.Option("--collector", help="Collector URL.")
        ] = None,
    ) -> None:
        """Search collected logs."""
        client = LogClient(_collector_url(collector))
        try:
            records = client.query(
                service=service, level=level, since=since, grep=grep, limit=limit
            )
        except ShipkitError as err:
            print_error(str(err))
            raise typer.Exit(code=1) from err
        finally:
            client.close()
        if not records:
            console.print("[yellow]No matching log lines.[/yellow]")
            return
        table = Table(title="Logs")
        table.add_column("Time")
        table.add_column("Service")
        table.add_column("Level")
        table.add_column("Message")
        for record in records:
            table.add_row(
                record.ts.strftime("%Y-%m-%d %H:%M:%S"),
                record.service,
                record.level,
                record.message,
            )
        console.print(table)
