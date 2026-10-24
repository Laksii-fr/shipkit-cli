# ShipKit

Developer tooling for monorepos. One CLI, three features:

1. **Change-aware CI** - `shipkit ci` works out which services a git
   change affects (including services that depend on them) and runs
   only their build/test steps, in parallel, inside Docker.
2. **Automated releases** - `shipkit release` bumps the semantic
   version from Conventional Commits, updates `CHANGELOG.md`, tags
   the commit, and can create a GitHub release.
3. **Log collection** - `shipkit run` runs a container and ships its
   logs in batches to a FastAPI + PostgreSQL collector service.
   `shipkit logs` searches them by service, level, time range and text.

Plus a composite **GitHub Action** (`action.yml`) that runs the CI
feature in a workflow with a few lines of YAML.

There is no seed or demo data anywhere in the product code. Every
result ShipKit prints comes from a real operation on your repo:
a real git diff, a real container run, a real database row.

## Demo

<video src="assets/shipkit-one-take-v5.mp4" controls width="100%" title="ShipKit demo">
  <a href="assets/shipkit-one-take-v5.mp4">Watch the ShipKit demo video</a>
</video>

## How to run

Step-by-step local setup (venv, dry-run, Docker Compose, tests):
see **[HOW_TO_RUN.md](HOW_TO_RUN.md)**.

## Install

```bash
# the CLI
cd cli && pip install -e ".[dev]"

# the collector (only if you run it outside Docker Compose)
cd collector && pip install -e ".[dev]"
```

Requires Python 3.11+, git on PATH, and Docker for the CI runner
and for `shipkit run`.

## shipkit.yml

One file at the root of your monorepo:

```yaml
services:
  common:
    path: libs/common
    image: python:3.12-slim
    test: "python -m pytest tests -q"
  api:
    path: services/api
    depends_on: [common]
    build: "pip install -e ."
    test: "python -m pytest tests -q"

release:
  version_file: VERSION        # plain-text file, default VERSION
  # github_repo: owner/repo    # optional, else parsed from origin
```

Validation is strict and friendly: unknown dependencies, missing
service paths, duplicate services and YAML errors are all reported
with the service name and the problem, never a stack trace.

## Usage

### Change-aware CI

```bash
shipkit ci                        # diff against main, run affected services
shipkit ci --base develop         # diff against another ref
shipkit ci --dry-run              # print the plan, run nothing
shipkit ci --all                  # run every service
shipkit ci --max-workers 8        # parallel services per layer
```

Steps: `git diff --name-only <base>...HEAD` → map files to services
by longest path prefix → expand to dependents (`depends_on`,
transitively) → order into topological layers with the standard
library `graphlib` → run each layer in parallel
(`ThreadPoolExecutor`), each service in a Docker container with its
folder mounted at `/work`. Results print as a Rich table
(service, status, measured duration) and are appended to
`$GITHUB_STEP_SUMMARY` when that variable is set. Exit code is
non-zero if any service fails; later layers are skipped when an
earlier layer fails.

Edge cases handled: no changes (nothing runs, exit 0), a changed
file outside every service (ignored), circular dependencies
(a clear error naming the cycle), Docker not running (one clear
sentence, not a traceback).

### Automated releases

```bash
shipkit release --dry-run         # plan only: bump, tag, changelog section
shipkit release                   # local: version file + CHANGELOG + commit + tag
shipkit release --push            # also push commit and tag to origin
shipkit release --push --github   # also create the GitHub release (GITHUB_TOKEN)
```

Commits since the last `v*` tag are parsed as Conventional Commits:
any breaking change (`feat!:` or a `BREAKING CHANGE:` footer) bumps
major, any `feat` bumps minor, everything else bumps patch.
Non-conventional commits are ignored (and counted in the plan).

### Log collection

Start the collector and Postgres:

```bash
docker compose up --build         # collector on http://localhost:8000
```

Run a container and ship its logs, then search them:

```bash
shipkit run api my-api-image
shipkit run demo alpine echo "ERROR boom"   # optional command replaces image CMD
shipkit logs --service api --level error --since 1h --grep timeout
```

`shipkit run` streams the container's stdout/stderr, detects each
line's level (JSON logs first, then `ERROR`/`WARN`/`INFO`/`DEBUG`
keywords, else INFO), buffers lines and POSTs them to the collector
in batches of 50. The collector starts empty and stores only what
it is sent.

Collector API:

| Endpoint | Description |
|---|---|
| `POST /ingest` | Body: `{"lines": [{service, ts, level, message}, ...]}`, returns 202 |
| `GET /logs?service=&level=&since=1h&q=` | Filtered search, newest first |
| `GET /health` | `{"status": "ok", "database": "ok"}` |

The logs table is indexed on `(service, ts)` and on `level`. Text
search is `ILIKE`; on Postgres it can be upgraded to a `tsvector`
column with a GIN index without changing the API. Migrations are
Alembic (`collector/migrations`), and Compose runs
`alembic upgrade head` before starting the collector.

Collector configuration is by environment:
`SHIPKIT_COLLECTOR_DATABASE_URL` (default
`postgresql+psycopg://shipkit:shipkit@localhost:5432/shipkit`).
The CLI reads the collector URL from `--collector` or
`SHIPKIT_COLLECTOR_URL` (default `http://localhost:8000`).

### GitHub Action

This repo's `action.yml` is a composite Action. See
`.github/workflows/demo-ci.yml` for a live example against
`examples/monorepo`.

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: your-org/shipkit@main   # this repo's action.yml
        with:
          base: main
          max-workers: "4"
          # config: shipkit.yml
          # repo: .                 # monorepo root if nested in a larger git repo
          # all: "false"            # set "true" to run every service
```

## Architecture

Module-per-feature. A module may import from `core/` but never
from another module. Command and route files stay thin: they parse
input and call the controller, where all the logic lives, so the
logic is testable without HTTP or the CLI.

```
shipkit/
  cli/
    pyproject.toml
    src/shipkit/
      main.py            # Typer app, registers each module's commands
      core/              # config.py, git.py, console.py, errors.py
      modules/
        ci/       command.py, controller.py, models.py, affected.py, runner.py, report.py
        release/  command.py, controller.py, models.py, commits.py, version.py, changelog.py, github_client.py
        logs/     command.py, controller.py, models.py, shipper.py, client.py
    tests/modules/{ci,release,logs}/
  collector/
    pyproject.toml, Dockerfile, alembic.ini, migrations/
    app/
      main.py            # create_app() factory, includes each module's router
      core/              # config.py (env settings), database.py (engine, session)
      modules/
        logs/    route.py, controller.py, model.py, schema.py, repository.py
        health/  route.py
    tests/
  examples/monorepo/     # a real tiny monorepo with 4 services, to try the tool on
  action.yml             # composite GitHub Action
  docker-compose.yml     # collector + Postgres
  .github/workflows/     # ShipKit's own CI + release workflows
```

## Demo

A complete walkthrough, including a demo script and interview
talking points, is in [DEMO.md](DEMO.md). Short version, on
`examples/monorepo` (common, api, worker, gateway):

- change only `services/api` → `shipkit ci --base main` runs `api`,
  then its dependent `gateway`
- change `libs/common` → it runs `common`, then `api` + `worker`
  in parallel, then `gateway`
- `shipkit release --dry-run` in that repo shows the version plan
  computed from its real commits

## Development

```bash
cd cli && pytest -q && ruff check src tests
cd ../collector && pytest -q && ruff check app tests
```

Tests run against real temporary git repositories, real subprocess
git, FastAPI's TestClient against a real (SQLite) database, and
httpx mock transports for the external GitHub/collector APIs. The
Docker daemon is faked only inside unit tests, behind the same
client interface the real Docker SDK satisfies; product code always
uses the real SDK and reports a clear error when Docker is down.
