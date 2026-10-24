"""Rendering a CI result: Rich table for people, markdown for GitHub."""

import os
from pathlib import Path

from rich.table import Table

from shipkit.core.console import console
from shipkit.modules.ci.models import CiResult

_STATUS_STYLE = {"passed": "green", "failed": "red", "planned": "yellow"}


def print_report(result: CiResult) -> None:
    if not result.plan.affected:
        console.print("[yellow]No affected services. Nothing to run.[/yellow]")
        return
    heading = "CI plan (dry run)" if result.dry_run else "CI results"
    table = Table(title=heading)
    table.add_column("Service")
    table.add_column("Status")
    table.add_column("Duration")
    for item in result.results:
        style = _STATUS_STYLE.get(item.status, "")
        table.add_row(
            item.service,
            f"[{style}]{item.status}[/{style}]" if style else item.status,
            f"{item.duration_seconds:.2f}s" if not result.dry_run else "-",
        )
    console.print(table)
    skipped = sorted(set(result.plan.affected) - {r.service for r in result.results})
    if skipped:
        console.print(f"[dim]Not run (earlier layer failed): {', '.join(skipped)}[/dim]")


def summary_markdown(result: CiResult) -> str:
    lines = ["## ShipKit CI", "", "| Service | Status | Duration (s) |", "|---|---|---|"]
    for item in result.results:
        lines.append(f"| {item.service} | {item.status} | {item.duration_seconds:.2f} |")
    if not result.results:
        lines.append("| - | no affected services | - |")
    return "\n".join(lines) + "\n"


def write_step_summary(result: CiResult, path: Path | None = None) -> Path | None:
    """Append the markdown summary to $GITHUB_STEP_SUMMARY when set."""
    target = path or (
        Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
    )
    if target is None:
        return None
    with target.open("a", encoding="utf-8") as handle:
        handle.write(summary_markdown(result))
    return target
