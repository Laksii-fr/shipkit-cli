# ShipKit demo

Prereqs: Python 3.11+, git, Docker running. Install once:

```bash
cd cli && pip install -e ".[dev]" && cd ..
```

## 1. Change-aware CI (on examples/monorepo)

```bash
cd examples/monorepo
git init -b main && git add . && git commit -m "feat: initial monorepo"
git checkout -b change-api
# edit services/api/apilib/__init__.py, commit it
shipkit ci --base main --dry-run    # plan: api (+ gateway, which depends on api)
shipkit ci --base main              # runs api then gateway in Docker

git checkout main && git checkout -b change-common
# edit libs/common/commonlib/__init__.py, commit it
shipkit ci --base main              # common, then api+worker in parallel, then gateway
```

Talking point: the saving is measurable. The second run does 4
services because everything depends on `common`; the first does 2
of 4 (`api` + dependent `gateway`). On a real monorepo that ratio
is the whole pitch.

## 2. Release

```bash
# in examples/monorepo, after some feat:/fix: commits on top of a tag
git tag v0.1.0   # if there is no tag yet; add a VERSION file with 0.1.0
shipkit release --dry-run   # shows current -> next, bump reason, changelog section
shipkit release             # updates VERSION + CHANGELOG.md, commits, tags vX.Y.Z
```

## 3. Logs

```bash
docker compose up --build           # from the repo root, another terminal
shipkit run api <your-service-image>   # an image whose process logs to stdout
shipkit logs --service api --level error --since 1h --grep timeout
curl http://localhost:8000/health
```

Note: `shipkit run` needs an image that actually logs. Use one of
your own service images; the example services are libraries, not
long-running containers, so they are not used for this step.

## Interview talking points

**CI / graph**
- Files map to services by *longest* path prefix, so nested services
  (`services/` and `services/api/`) resolve correctly.
- Dependents expansion is a reverse-graph BFS; ordering is
  `graphlib.TopologicalSorter.get_ready()` in a loop, which gives
  parallel layers for free and raises `CycleError`, which we convert
  into a user-readable message.
- Threads, not processes: the work is waiting on containers, so a
  `ThreadPoolExecutor` per layer is enough, and a failed layer stops
  its dependents.

**Release**
- Bump rules are pure functions of the parsed commit list, so the
  whole matrix (breaking/feat/fix/other) is unit tested without git.
- `--dry-run` is the same code path with writes disabled, and
  push/GitHub are opt-in flags: a local run can never publish
  anything by accident.

**Logs**
- Batching (50 lines per POST) because one request per line would
  drown both the CLI and the collector under a chatty container.
- Level detection tries JSON first because structured logs are
  unambiguous; keyword search is the fallback for plain text.
- Indexes follow the query patterns: `(service, ts)` for the common
  filter, `level` for severity scans. ILIKE now, tsvector+GIN is the
  documented Postgres upgrade, isolated in the repository layer.
- The collector and the CLI are separate packages on purpose: server
  dependencies (FastAPI, Postgres drivers) never land on a
  developer's machine just to run CI, and vice versa.

**Resume bullet (honest, fill the bracket from your own demo run)**
> ShipKit - Python CLI (Typer, graphlib, Docker SDK) for monorepos:
> change-aware CI that runs only services affected by a git change
> and their dependents, in parallel Docker containers ([X] of
> [Y] services skipped on a single-service change in the demo repo);
> Conventional-Commits release automation (semver, changelog, tag,
> GitHub release); FastAPI + PostgreSQL log collector with batched
> shipping and filtered search. [89 CLI + 10 collector tests, pytest.]
