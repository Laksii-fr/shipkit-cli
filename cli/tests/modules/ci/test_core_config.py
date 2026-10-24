"""Phase 1: shipkit.yml loading and validation."""

from pathlib import Path

import pytest

from shipkit.core.config import load_config
from shipkit.core.errors import ShipkitError

VALID_YML = """
services:
  common:
    path: libs/common
  api:
    path: services/api
    depends_on: [common]
    test: "pytest -q"
"""


def write_repo(tmp_path: Path, yml: str) -> Path:
    (tmp_path / "libs" / "common").mkdir(parents=True)
    (tmp_path / "services" / "api").mkdir(parents=True)
    config = tmp_path / "shipkit.yml"
    config.write_text(yml)
    return config


def test_load_valid_config(tmp_path):
    config_path = write_repo(tmp_path, VALID_YML)
    config = load_config(config_path)
    assert set(config.services) == {"common", "api"}
    assert config.services["api"].depends_on == ["common"]
    assert config.services["api"].name == "api"
    assert config.services["api"].image == "python:3.12-slim"
    assert config.release.version_file == "VERSION"


def test_missing_file_is_clear_error(tmp_path):
    with pytest.raises(ShipkitError, match="not found"):
        load_config(tmp_path / "shipkit.yml")


def test_invalid_yaml_is_clear_error(tmp_path):
    config_path = write_repo(tmp_path, "services: [unclosed\n")
    with pytest.raises(ShipkitError, match="YAML syntax error"):
        load_config(config_path)


def test_unknown_dependency_is_clear_error(tmp_path):
    yml = VALID_YML.replace("depends_on: [common]", "depends_on: [nope]")
    config_path = write_repo(tmp_path, yml)
    with pytest.raises(ShipkitError, match="unknown service 'nope'"):
        load_config(config_path)


def test_missing_path_is_clear_error(tmp_path):
    yml = VALID_YML.replace("path: libs/common", "path: libs/gone")
    config_path = write_repo(tmp_path, yml)
    with pytest.raises(ShipkitError, match="does not exist"):
        load_config(config_path)


def test_self_dependency_is_clear_error(tmp_path):
    yml = """
services:
  api:
    path: services/api
    depends_on: [api]
"""
    config_path = write_repo(tmp_path, yml)
    with pytest.raises(ShipkitError, match="depend on itself"):
        load_config(config_path)


def test_duplicate_service_is_clear_error(tmp_path):
    yml = """
services:
  api:
    path: services/api
  api:
    path: services/api
"""
    config_path = write_repo(tmp_path, yml)
    with pytest.raises(ShipkitError, match="duplicate service 'api'"):
        load_config(config_path)


def test_missing_path_field_reports_field(tmp_path):
    yml = """
services:
  api:
    depends_on: []
"""
    config_path = write_repo(tmp_path, yml)
    with pytest.raises(ShipkitError, match="path"):
        load_config(config_path)


def test_no_services_is_clear_error(tmp_path):
    config_path = write_repo(tmp_path, "release:\n  version_file: VERSION\n")
    with pytest.raises(ShipkitError, match="at least one service"):
        load_config(config_path)
