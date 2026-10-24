"""Phase 2: Docker runner with a fake Docker client (tests only)."""

from pathlib import Path

from docker.errors import DockerException

from shipkit.core.config import ServiceConfig
from shipkit.modules.ci.runner import DockerRunner


class FakeContainers:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, image, command, volumes=None, working_dir=None, remove=None):
        self.calls.append(
            {"image": image, "command": command, "volumes": volumes, "working_dir": working_dir}
        )
        shell_command = command[-1] if isinstance(command, list) else str(command)
        if "fail" in shell_command:
            raise DockerException("container exited with code 1")
        return b"tests passed"


class FakeClient:
    def __init__(self) -> None:
        self.containers = FakeContainers()


def make_service(tmp_path: Path, **kwargs) -> ServiceConfig:
    defaults = {"name": "api", "path": "services/api", "test": "pytest -q"}
    defaults.update(kwargs)
    return ServiceConfig(**defaults)


def test_runner_runs_test_command_in_service_mount(tmp_path):
    client = FakeClient()
    runner = DockerRunner(client=client)
    service_dir = tmp_path / "services" / "api"
    service_dir.mkdir(parents=True)
    result = runner.run_service(make_service(tmp_path), tmp_path)
    assert result.status == "passed"
    assert result.duration_seconds >= 0
    call = client.containers.calls[0]
    assert call["image"] == "python:3.12-slim"
    assert call["working_dir"] == "/work"
    assert str(service_dir.resolve()) in call["volumes"]


def test_runner_runs_build_before_test(tmp_path):
    client = FakeClient()
    runner = DockerRunner(client=client)
    (tmp_path / "services" / "api").mkdir(parents=True)
    runner.run_service(make_service(tmp_path, build="pip install .", test="pytest"), tmp_path)
    assert len(client.containers.calls) == 1
    assert client.containers.calls[0]["command"][-1] == "pip install . && pytest"


def test_runner_marks_failure_and_stops(tmp_path):
    client = FakeClient()
    runner = DockerRunner(client=client)
    (tmp_path / "services" / "api").mkdir(parents=True)
    result = runner.run_service(
        make_service(tmp_path, build="fail build", test="pytest"), tmp_path
    )
    assert result.status == "failed"
    assert len(client.containers.calls) == 1  # single container; script stops at fail


def test_runner_no_commands_is_passed(tmp_path):
    runner = DockerRunner(client=FakeClient())
    (tmp_path / "services" / "api").mkdir(parents=True)
    result = runner.run_service(make_service(tmp_path, test=None, build=None), tmp_path)
    assert result.status == "passed"
