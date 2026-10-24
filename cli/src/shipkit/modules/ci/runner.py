"""Running one service's build + test steps, in Docker.

The Docker client is obtained through a small factory so tests can
inject a fake client. Product code always talks to the real Docker
SDK; if the daemon is unreachable the user gets one clear sentence,
not a stack trace.
"""

import time
from pathlib import Path
from typing import Protocol

import docker
from docker.errors import DockerException

from shipkit.core.config import ServiceConfig
from shipkit.core.errors import ShipkitError
from shipkit.modules.ci.models import ServiceRunResult


class DockerClientProtocol(Protocol):
    """The slice of the Docker SDK client this runner uses."""

    containers: object


def create_docker_client() -> DockerClientProtocol:
    """Create a real Docker client, or fail with a clear message."""
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


class DockerRunner:
    """Runs services in containers, one service folder mounted at /work."""

    def __init__(self, client: DockerClientProtocol | None = None) -> None:
        self._client = client if client is not None else create_docker_client()

    def run_service(self, service: ServiceConfig, repo_root: Path) -> ServiceRunResult:
        service_dir = (repo_root / service.path).resolve()
        commands = [cmd for cmd in (service.build, service.test) if cmd]
        if not commands:
            return ServiceRunResult(
                service=service.name, status="passed", output="no build/test commands"
            )
        # One container per service so build installs survive into test.
        script = " && ".join(commands)
        started = time.monotonic()
        try:
            raw = self._client.containers.run(  # type: ignore[attr-defined]
                service.image,
                ["sh", "-lc", script],
                volumes={str(service_dir): {"bind": "/work", "mode": "rw"}},
                working_dir="/work",
                remove=True,
            )
        except DockerException as err:
            return ServiceRunResult(
                service=service.name,
                status="failed",
                duration_seconds=round(time.monotonic() - started, 3),
                output=f"$ {script}\n{err}",
            )
        if isinstance(raw, bytes):
            body = raw.decode("utf-8", "replace").strip()
            output = f"$ {script}\n{body}" if body else f"$ {script}"
        elif raw:
            output = f"$ {script}\n{str(raw).strip()}"
        else:
            output = f"$ {script}"
        return ServiceRunResult(
            service=service.name,
            status="passed",
            duration_seconds=round(time.monotonic() - started, 3),
            output=output,
        )
