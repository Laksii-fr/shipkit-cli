"""Phase 1: affected-services logic."""

import pytest

from shipkit.core.config import ShipkitConfig
from shipkit.core.errors import ShipkitError
from shipkit.modules.ci.affected import (
    build_plan,
    direct_services,
    expand_dependents,
    service_for_file,
    topological_layers,
)

CONFIG_DICT = {
    "services": {
        "common": {"path": "libs/common"},
        "api": {"path": "services/api", "depends_on": ["common"]},
        "worker": {"path": "services/worker", "depends_on": ["common"]},
        "gateway": {"path": "services/gateway", "depends_on": ["api"]},
    }
}


def make_config(**overrides):
    data = {**CONFIG_DICT, **overrides}
    config = ShipkitConfig.model_validate(data)
    for name, svc in config.services.items():
        svc.name = name
    return config


def test_file_maps_to_owning_service():
    config = make_config()
    assert service_for_file(config, "services/api/main.py") == "api"
    assert service_for_file(config, "libs/common/util.py") == "common"


def test_file_outside_every_service_is_ignored():
    config = make_config()
    assert service_for_file(config, "README.md") is None
    assert direct_services(config, ["docs/notes.md"]) == set()


def test_longest_prefix_wins_for_nested_services():
    config = ShipkitConfig.model_validate(
        {
            "services": {
                "all_services": {"path": "services"},
                "api": {"path": "services/api"},
            }
        }
    )
    assert service_for_file(config, "services/api/x.py") == "api"
    assert service_for_file(config, "services/other/y.py") == "all_services"


def test_direct_change_does_not_pull_in_unrelated():
    plan = build_plan(make_config(), ["services/worker/jobs.py"])
    assert plan.direct == ["worker"]
    assert plan.affected == ["worker"]


def test_common_change_expands_to_all_dependents_transitively():
    plan = build_plan(make_config(), ["libs/common/util.py"])
    assert plan.direct == ["common"]
    assert plan.affected == ["api", "common", "gateway", "worker"]


def test_layers_respect_dependency_order():
    plan = build_plan(make_config(), ["libs/common/util.py"])
    assert plan.layers == [["common"], ["api", "worker"], ["gateway"]]


def test_no_changes_gives_empty_plan():
    plan = build_plan(make_config(), [])
    assert plan.affected == []
    assert plan.layers == []


def test_cycle_is_a_clear_error_not_a_traceback():
    config = ShipkitConfig.model_validate(
        {
            "services": {
                "a": {"path": "a", "depends_on": ["b"]},
                "b": {"path": "b", "depends_on": ["a"]},
            }
        }
    )
    with pytest.raises(ShipkitError, match="Circular dependency"):
        topological_layers(config, {"a", "b"})


def test_expand_dependents_from_middle_of_graph():
    config = make_config()
    assert expand_dependents(config, {"api"}) == {"api", "gateway"}
