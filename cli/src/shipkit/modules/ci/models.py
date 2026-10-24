"""Data models for the CI feature, passed between controller layers."""

from typing import Literal

from pydantic import BaseModel, Field

ServiceStatus = Literal["passed", "failed", "planned"]


class CiPlan(BaseModel):
    """What a CI run will do, before anything is executed."""

    changed_files: list[str] = Field(default_factory=list)
    direct: list[str] = Field(default_factory=list)
    affected: list[str] = Field(default_factory=list)
    layers: list[list[str]] = Field(default_factory=list)


class ServiceRunResult(BaseModel):
    """The outcome of running one service's build + test steps."""

    service: str
    status: ServiceStatus
    duration_seconds: float = 0.0
    output: str = ""


class CiResult(BaseModel):
    """The full result of a `shipkit ci` run."""

    plan: CiPlan
    results: list[ServiceRunResult] = Field(default_factory=list)
    dry_run: bool = False

    @property
    def success(self) -> bool:
        return all(result.status != "failed" for result in self.results)

    @property
    def exit_code(self) -> int:
        return 0 if self.success else 1
