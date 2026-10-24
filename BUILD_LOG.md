# BUILD_LOG - ShipKit

Built phase by phase (Phases 1-7) on top of the verified Phase 0
skeleton, each phase tested before the next started. Environment:
Python 3.12 in a venv under /tmp (recreated once after /tmp was
wiped mid-build; all suites were re-run after recreation).

## Phase 1 - core + CI affected logic
Built: `core/errors.py` (ShipkitError), `core/console.py`,
`core/config.py` (Pydantic load/validate of shipkit.yml: unknown
dependency, self-dependency, duplicate service via a YAML node
pass, missing path, YAML syntax, field errors - all as clear
ShipkitErrors), `core/git.py` (subprocess git: repo_root,
changed_files with base verification, latest_tag, commits_since,
remote slug), `modules/ci/models.py`, `modules/ci/affected.py`
(longest-prefix mapping, transitive dependents BFS, graphlib
layers, cycle -> ShipkitError).
Tests: 25 new (affected 9, config 9, git 7 on real temp git
repos) - all passed. Ruff clean after one import-sort fix.

## Phase 2 - CI runner/controller/command + example monorepo
Built: `runner.py` (Docker SDK, service dir mounted at /work,
build then test via `sh -lc`, measured duration, daemon-down ->
one clear error), `controller.py` (layers run with
ThreadPoolExecutor, failed layer stops dependents, dry-run and
--all paths), `report.py` (Rich table + $GITHUB_STEP_SUMMARY
markdown), `command.py` (Annotated Typer options).
Also `examples/monorepo`: common/api/worker/gateway, real code,
each service's own pytest suite verified passing stand-alone
(2 tests each), plus the PYTHONPATH production-wiring example
in `apilib/main.py` executed successfully.
Tests: 13 new (runner 4 with a fake Docker client, controller 6
on real temp git repos with a recording runner, report 3).
Live check: `shipkit ci --dry-run --all` on the example renders
the 4-service plan in correct layer order. Real (non-dry) run in
this VM correctly produces the "Docker is not running" error -
see Limitations.

## Phase 3 - GitHub Action + project workflows
Built: root `action.yml` (composite: setup-python, pip install
./cli, shipkit ci with base/max-workers/config inputs),
`.github/workflows/ci.yml` (install both packages, ruff, pytest
per package) and `release.yml` (workflow_dispatch dry-run default,
tags, calls shipkit release). All three files parse as valid YAML
and the action's `runs.using` is `composite`.

## Phase 4 - release module
Built: `commits.py` (Conventional Commits incl. `!` and both
BREAKING footer spellings, non-conventional ignored+counted),
`version.py` (SemVer parse/bump), `changelog.py` (grouped
Breaking/Features/Fixes/Other, prepend preserving history and
the `# Changelog` header), `github_client.py` (httpx POST
releases, clear HTTP errors), `controller.py` (plan from the
real repo: last tag, commits since; execute writes the version
file - `release.version_file`, default `VERSION` - prepends the
changelog, commits, tags; push/GitHub only on explicit flags),
`command.py`.
Tests: 35 new (parsing matrix, bump matrix, changelog,
controller on real temp git repos: plan minor/major, dry-run
changes nothing, full local release updates VERSION+CHANGELOG+
tag; GitHub client via MockTransport).
Problems found and fixed: (1) test helper tried to append to a
not-yet-existing file - fixed the helper; (2) the release commit
failed on a temp repo with no git identity - the fixture now sets
a repo-local identity (never global), and real users' repos carry
their own config.

## Phase 5 - collector service
Built: `core/config.py` (pydantic-settings,
SHIPKIT_COLLECTOR_ prefix), `core/database.py` (Database factory
on app.state, no globals), logs module (model with (service, ts)
and level indexes; schema normalising level case and timestamps
to naive UTC; repository as the only SQL layer, ILIKE search;
controller with since parsing 30m/1h/2d; thin routes POST
/ingest 202, GET /logs), health route (status + DB check),
`app/main.py` create_app factory, Alembic env + hand-written
initial revision coherent with the model, Dockerfile,
root docker-compose.yml (Postgres 16 with healthcheck, collector
depending on healthy DB, running migrations on start).
Tests: 10 new, FastAPI TestClient against a real SQLite file DB:
health, starts-empty, ingest+query order, service/level/text/
since filters, combined filters, invalid since -> 400, schema
422. Additionally the Alembic migration was really executed
against SQLite and created the `logs` table.
Problem fixed: a helper function inserted between import blocks
tripped ruff E402 - imports reordered.

## Phase 6 - CLI logs module
Built: `models.py`, `shipper.py` (buffer, flush at 50, flush on
close, clear unreachable-collector error), `client.py` (GET /logs
with service/level/since/q, 400 detail surfaced), `controller.py`
(level detection - JSON first, earliest keyword otherwise, INFO
default; container streaming through the Docker SDK with the
same daemon-down error as CI), `command.py` (`shipkit run`,
`shipkit logs` Rich table, --collector / SHIPKIT_COLLECTOR_URL).
Tests: 15 new (level matrix, JSON variants, fake Docker
streaming, shipper batch boundaries [3,3,1] for 7 lines at batch
3, unreachable collector error, client param building, 400).
Live integration (in-process server, real HTTP): uvicorn served
the collector on SQLite - GET /health ok, POST /ingest accepted
1, GET /logs?q= returned the row, and `shipkit logs --service api
--grep timeout` against it printed the row in the Rich table.
Problem found: this VM's NO_PROXY contains bracketed IPv6 entries
that this httpx version fails to parse when constructing a
default client - worked around in one test fixture by injecting
a client. On a normal machine this does not occur; the CLI accepts
standard proxy environments.

## Phase 7 - docs, final verification
Built: root README.md (problem, install, shipkit.yml, all
commands, collector API, Compose, Action usage, architecture
with the import rules, development), DEMO.md (demo script +
interview talking points + an honest resume bullet with a
bracket to fill from the reader's own measured demo).
Final verification, all in the recreated venv:
- CLI: 89 tests passed. Collector: 10 tests passed. Total 99.
- Ruff: clean on cli src+tests, collector app+tests+migrations.
- Help: `shipkit --help`, `ci`, `release`, `run`, `logs` --help
  all exit 0 and render.
- Docker-down paths for both `ci` (real run) and `run` print the
  single clear error, exit non-zero, no traceback.

## Honest limitations
- **Docker is not available in this VM** (no docker binary, no
  daemon, no Postgres server). Container execution in the CI
  runner and in `shipkit run`, and the Docker Compose stack, are
  therefore verified by unit tests with fake clients (behind the
  same interfaces the real SDK objects satisfy), by the
  daemon-down error paths exercised for real, and by code/YAML
  inspection - NOT by a live container run. To verify on a machine
  with Docker: `cd examples/monorepo`, follow DEMO.md section 1,
  and `docker compose up --build` at the root for section 3.
- Collector tests run on SQLite by design; the Postgres path
  differs only in driver/URL and the ILIKE operator, which the
  repository isolates in one function. Migrations were executed
  for real against SQLite.
- ShipKit's own git history starts at the Phase 7 commit; the
  release workflow's push/GitHub steps have not been executed
  against a real GitHub remote (the client is MockTransport
  tested, and push/github are opt-in flags).
