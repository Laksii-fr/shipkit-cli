"""Phase 6: level detection and run_container with a fake Docker client."""

import pytest

from shipkit.modules.logs.controller import detect_level, run_container
from shipkit.modules.logs.models import LogLine
from shipkit.modules.logs.shipper import LogShipper


@pytest.mark.parametrize(
    "line,level",
    [
        ("INFO server started", "info"),
        ("ERROR database timeout", "error"),
        ("WARN cache is cold", "warn"),
        ("WARNING cache is cold", "warn"),
        ("DEBUG retrying request", "debug"),
        ("just a plain line", "info"),
        ("CRITICAL out of memory", "error"),
    ],
)
def test_detect_level_keywords(line, level):
    detected, message = detect_level(line)
    assert detected == level
    assert message == line


def test_detect_level_json():
    level, message = detect_level('{"level": "error", "message": "boom happened"}')
    assert level == "error"
    assert message == "boom happened"


def test_detect_level_json_severity_and_msg():
    level, message = detect_level('{"severity": "WARNING", "msg": "slow query"}')
    assert level == "warn"
    assert message == "slow query"


def test_detect_level_bad_json_falls_back_to_keywords():
    level, _ = detect_level("{not json ERROR here")
    assert level == "error"


class FakeContainer:
    def logs(self, stream=True, follow=True):
        yield b"INFO starting up\n"
        yield b"ERROR something broke\n"
        yield b'{"level": "warn", "message": "json warning"}\n'


class FakeContainers:
    def run(self, image, detach=True):
        assert detach is True
        return FakeContainer()


class FakeDockerClient:
    containers = FakeContainers()


class CapturingShipper(LogShipper):
    def __init__(self) -> None:
        import httpx

        dummy = httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(202, json={}))
        )
        super().__init__("http://collector", batch_size=100, client=dummy)
        self.lines: list[LogLine] = []

    def add(self, line: LogLine) -> None:  # capture instead of sending
        self.lines.append(line)
        self.shipped += 1


def test_run_container_streams_detects_and_ships():
    shipper = CapturingShipper()
    count = run_container(
        service="api",
        image="api:latest",
        collector_url="http://unused",
        docker_client=FakeDockerClient(),
        shipper=shipper,
    )
    assert count == 3
    assert [line.level for line in shipper.lines] == ["info", "error", "warn"]
    assert all(line.service == "api" for line in shipper.lines)
    assert shipper.lines[2].message == "json warning"
