"""Which services does a change affect?

Pure logic, no IO: given the config and a list of changed file paths,
work out the directly changed services, expand to everything that
(transitively) depends on them, and order the result into
topological layers that can run in parallel.
"""

from graphlib import CycleError, TopologicalSorter
from pathlib import PurePosixPath

from shipkit.core.config import ShipkitConfig
from shipkit.core.errors import ShipkitError
from shipkit.modules.ci.models import CiPlan


def _normalise(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix().strip("./")


def service_for_file(config: ShipkitConfig, file_path: str) -> str | None:
    """The service owning a file, by longest matching path prefix."""
    normalised = _normalise(file_path)
    best_name: str | None = None
    best_len = -1
    for name, service in config.services.items():
        prefix = _normalise(service.path)
        if normalised == prefix or normalised.startswith(prefix + "/"):
            if len(prefix) > best_len:
                best_name = name
                best_len = len(prefix)
    return best_name


def direct_services(config: ShipkitConfig, changed_files: list[str]) -> set[str]:
    """Services that own at least one changed file. Others are ignored."""
    found: set[str] = set()
    for file_path in changed_files:
        name = service_for_file(config, file_path)
        if name is not None:
            found.add(name)
    return found


def expand_dependents(config: ShipkitConfig, direct: set[str]) -> set[str]:
    """Direct services plus every service that transitively depends on them."""
    dependents_of: dict[str, set[str]] = {name: set() for name in config.services}
    for name, service in config.services.items():
        for dep in service.depends_on:
            dependents_of[dep].add(name)

    affected = set(direct)
    queue = list(direct)
    while queue:
        current = queue.pop()
        for dependent in dependents_of[current]:
            if dependent not in affected:
                affected.add(dependent)
                queue.append(dependent)
    return affected


def topological_layers(config: ShipkitConfig, affected: set[str]) -> list[list[str]]:
    """Group affected services into layers.

    Layer 0 has no (affected) dependencies, layer 1 depends only on
    layer 0, and so on. Services inside one layer can run in parallel.
    A dependency cycle is a clear ShipkitError, not a traceback.
    """
    if not affected:
        return []
    graph: dict[str, set[str]] = {
        name: {dep for dep in config.services[name].depends_on if dep in affected}
        for name in affected
    }
    sorter = TopologicalSorter(graph)
    try:
        sorter.prepare()
    except CycleError as err:
        cycle = " -> ".join(err.args[1]) if len(err.args) > 1 else "unknown cycle"
        raise ShipkitError(
            f"Circular dependency detected in shipkit.yml: {cycle}. "
            "Break the cycle in depends_on to run CI."
        ) from err
    layers: list[list[str]] = []
    while sorter.is_active():
        ready = sorted(sorter.get_ready())
        layers.append(ready)
        sorter.done(*ready)
    return layers


def build_plan(config: ShipkitConfig, changed_files: list[str]) -> CiPlan:
    """Full plan for a list of changed files."""
    direct = direct_services(config, changed_files)
    affected = expand_dependents(config, direct)
    layers = topological_layers(config, affected)
    return CiPlan(
        changed_files=list(changed_files),
        direct=sorted(direct),
        affected=sorted(affected),
        layers=layers,
    )


def plan_for_all(config: ShipkitConfig) -> CiPlan:
    """Plan that runs every service (the --all case)."""
    affected = set(config.services)
    return CiPlan(
        changed_files=[],
        direct=sorted(affected),
        affected=sorted(affected),
        layers=topological_layers(config, affected),
    )
