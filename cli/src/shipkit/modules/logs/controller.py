"""Logs logic: level detection and streaming a container to the collector.

Level detection order matters: a JSON log line speaks for itself,
otherwise the earliest level keyword in the line wins, otherwise
the line is INFO.
"""

import json
import re
from datetime import UTC, datetime
from typing import Protocol

import docker
from docker.errors import DockerException

from shipkit.core.errors import ShipkitError
from shipkit.modules.logs.models import LogLine
from shipkit.modules.logs.shipper import LogShipper

_LEVEL_WORDS = ["ERROR", "CRITICAL", "WARN", "WARNING", "INFO", "DEBUG"]
_LEVEL_PATTERN = re.compile(r"\b(" + "|".join(_LEVEL_WORDS) + r")\b")
_LEVEL_ALIASES = {"WARNING": "warn", "CRITICAL": "error"}


def detect_level(raw_line: str) -> tuple[str, str]:
    """Return (level, message) for one raw output line."""
    text = raw_line.strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            level = str(data.get("level") or data.get("severity") or "info").lower()
            message = str(data.get("message") or data.get("msg") or text)
            return _LEVEL_ALIASES.get(level.upper(), level), message
    match = _LEVEL_PATTERN.search(text.upper())
    if match:
        word = match.group(1)
        return _LEVEL_ALIASES.get(word, word.lower()), text
    return "info", text


class ContainerProtocol(Protocol):
    def logs(self, stream: bool = True, follow: bool = True): ...

    def stop(self, timeout: int = 5) -> None: ...

    def remove(self, force: bool = True) -> None: ...


class DockerClientProtocol(Protocol):
    containers: object


def create_docker_client() -> DockerClientProtocol:
    """Real Docker client, or one clear error if the daemon is down."""
    try:
        client = docker.from_env()
        client.ping()
    except DockerException as err:
        raise ShipkitError(
            "Docker is not running or not reachable. "
            "Start Docker and try again. "
            f"(Docker said: {err})"
        ) from err
    return client


def _cleanup_container(container: object) -> None:
    """Stop and remove a container; never raise into the caller."""
    try:
        stop = getattr(container, "stop", None)
        if callable(stop):
            stop(timeout=5)
    except Exception:  # noqa: BLE001 - cleanup must not mask the real error
        pass
    try:
        remove = getattr(container, "remove", None)
        if callable(remove):
            remove(force=True)
    except Exception:  # noqa: BLE001
        pass


def run_container(
    *,
    service: str,
    image: str,
    collector_url: str,
    command: list[str] | None = None,
    docker_client: DockerClientProtocol | None = None,
    shipper: LogShipper | None = None,
) -> int:
    """Run a container, ship its output to the collector. Returns lines shipped."""
    client = docker_client or create_docker_client()
    own_shipper = shipper is None
    sender = shipper or LogShipper(collector_url)
    container = None
    try:
        run_kwargs: dict = {"detach": True}
        if command:
            run_kwargs["command"] = command
        container = client.containers.run(image, **run_kwargs)  # type: ignore[attr-defined]
        for raw in container.logs(stream=True, follow=True):
            line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
            for single in line.splitlines():
                if not single.strip():
                    continue
                level, message = detect_level(single)
                sender.add(
                    LogLine(
                        service=service,
                        ts=datetime.now(UTC),
                        level=level,
                        message=message,
                    )
                )
    finally:
        if container is not None:
            _cleanup_container(container)
        if own_shipper:
            sender.close()  # flushes the remaining buffered lines
    return sender.shipped
