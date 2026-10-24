"""ShipKit CLI entry point.

Phase 0 skeleton: creates the Typer app only. Each feature module
(ci, release, logs) registers its commands here in its own phase.
"""

import typer

__version__ = "0.1.0"

app = typer.Typer(
    name="shipkit",
    help="Developer tooling for monorepos: change-aware CI, releases, logs.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the ShipKit version."""
    typer.echo(f"shipkit {__version__}")


@app.command()
def about() -> None:
    """Print what ShipKit does."""
    typer.echo(
        "ShipKit: change-aware CI, automated releases, "
        "and log collection for monorepos."
    )


from shipkit.modules.ci.command import register as _register_ci  # noqa: E402
from shipkit.modules.logs.command import register as _register_logs  # noqa: E402
from shipkit.modules.release.command import register as _register_release  # noqa: E402

_register_ci(app)
_register_release(app)
_register_logs(app)


if __name__ == "__main__":
    app()
