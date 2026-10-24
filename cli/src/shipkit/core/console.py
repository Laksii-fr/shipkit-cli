"""Shared Rich console helpers.

Only presentation lives here. Business logic never prints; controllers
return data and command/report files render it.
"""

from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def print_error(message: str) -> None:
    """Print an error message in red to stderr."""
    err_console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    console.print(f"[green]{message}[/green]")
