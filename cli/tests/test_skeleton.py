"""Phase 0 smoke test: the CLI app exists and shows help."""

from typer.testing import CliRunner

from shipkit.main import app

runner = CliRunner()


def test_help_runs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "shipkit" in result.output.lower()
