"""Loading and validation of shipkit.yml.

The config file describes a monorepo:

    services:
      common:
        path: libs/common
      api:
        path: services/api
        depends_on: [common]
        build: "pip install -e ."
        test: "pytest -q"
    release:
      version_file: VERSION

All validation problems are reported as ShipkitError with a message
that names the file, the service, and what is wrong.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from shipkit.core.errors import ShipkitError


class ServiceConfig(BaseModel):
    """One service in the monorepo."""

    name: str = ""
    path: str
    depends_on: list[str] = Field(default_factory=list)
    build: str | None = None
    test: str | None = None
    image: str = "python:3.12-slim"


class ReleaseConfig(BaseModel):
    """Settings for `shipkit release`."""

    version_file: str = "VERSION"
    github_repo: str | None = None


class ShipkitConfig(BaseModel):
    """The whole shipkit.yml file."""

    services: dict[str, ServiceConfig]
    release: ReleaseConfig = Field(default_factory=ReleaseConfig)


def _check_duplicate_service_keys(path: Path, raw_text: str) -> None:
    """Reject duplicate service names, which PyYAML would silently merge."""
    try:
        node = yaml.compose(raw_text)
    except yaml.YAMLError:
        return  # the real parse below will report the syntax error
    if not isinstance(node, yaml.MappingNode):
        return
    for key_node, value_node in node.value:
        if getattr(key_node, "value", None) != "services":
            continue
        if not isinstance(value_node, yaml.MappingNode):
            continue
        seen: set[str] = set()
        for service_key, _ in value_node.value:
            name = getattr(service_key, "value", "")
            if name in seen:
                raise ShipkitError(f"{path}: duplicate service '{name}' in shipkit.yml")
            seen.add(name)


def _format_validation_error(path: Path, err: ValidationError) -> str:
    lines = [f"{path}: invalid shipkit.yml:"]
    for issue in err.errors():
        location = ".".join(str(part) for part in issue["loc"])
        lines.append(f"  - {location}: {issue['msg']}")
    return "\n".join(lines)


def load_config(config_path: Path, *, check_paths: bool = True) -> ShipkitConfig:
    """Load and validate a shipkit.yml file.

    Raises ShipkitError with a clear message on any problem.
    """
    path = Path(config_path)
    if not path.is_file():
        raise ShipkitError(
            f"Config file not found: {path}\n"
            "Run ShipKit from a repo with a shipkit.yml, or pass --config."
        )
    raw_text = path.read_text(encoding="utf-8")
    _check_duplicate_service_keys(path, raw_text)
    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as err:
        raise ShipkitError(f"{path}: YAML syntax error: {err}") from err
    if not isinstance(raw, dict):
        raise ShipkitError(f"{path}: shipkit.yml must be a mapping with a 'services' key")
    if not raw.get("services"):
        raise ShipkitError(f"{path}: shipkit.yml must define at least one service under 'services'")
    try:
        config = ShipkitConfig.model_validate(raw)
    except ValidationError as err:
        raise ShipkitError(_format_validation_error(path, err)) from err

    for name, service in config.services.items():
        service.name = name
    _validate_services(path, config, check_paths=check_paths)
    return config


def _validate_services(path: Path, config: ShipkitConfig, *, check_paths: bool) -> None:
    root = path.parent
    for name, service in config.services.items():
        for dep in service.depends_on:
            if dep == name:
                raise ShipkitError(f"{path}: service '{name}' cannot depend on itself")
            if dep not in config.services:
                raise ShipkitError(
                    f"{path}: service '{name}' depends on unknown service '{dep}'. "
                    f"Known services: {', '.join(sorted(config.services))}"
                )
        if check_paths and not (root / service.path).is_dir():
            raise ShipkitError(
                f"{path}: service '{name}' has path '{service.path}' "
                "which does not exist in the repo"
            )


def find_config(start: Path) -> Path:
    """Find shipkit.yml in `start` or any parent directory."""
    current = Path(start).resolve()
    for candidate_dir in [current, *current.parents]:
        candidate = candidate_dir / "shipkit.yml"
        if candidate.is_file():
            return candidate
    raise ShipkitError(
        f"No shipkit.yml found in {start} or any parent directory. "
        "Create one describing your services."
    )
