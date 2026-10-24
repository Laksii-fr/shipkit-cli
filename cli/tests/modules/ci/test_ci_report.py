"""Phase 2: step summary writing."""

from pathlib import Path

from shipkit.modules.ci.models import CiPlan, CiResult, ServiceRunResult
from shipkit.modules.ci.report import summary_markdown, write_step_summary


def make_result() -> CiResult:
    return CiResult(
        plan=CiPlan(affected=["api"], direct=["api"], layers=[["api"]]),
        results=[ServiceRunResult(service="api", status="passed", duration_seconds=1.5)],
    )


def test_summary_markdown_contains_rows():
    md = summary_markdown(make_result())
    assert "| api | passed | 1.50 |" in md


def test_write_step_summary_appends(tmp_path: Path):
    target = tmp_path / "summary.md"
    write_step_summary(make_result(), path=target)
    write_step_summary(make_result(), path=target)
    assert target.read_text().count("ShipKit CI") == 2


def test_write_step_summary_noop_without_env(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert write_step_summary(make_result()) is None
