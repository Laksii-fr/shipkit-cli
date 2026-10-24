# How to run ShipKit (local)

Prereqs: **Python 3.11+**, **git**, and **Docker Desktop** (for real CI container runs and the log collector).

If `python` or `docker` is not on your PATH, add your Python install (and its `Scripts` folder) and Docker’s `bin` folder, then confirm with `python --version` and `docker info`.

---

## 1. Install the CLI

From the repo root:

```bash
cd cli
python -m venv .venv

# Windows (Git Bash / bash)
source .venv/Scripts/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -U pip
pip install -e ".[dev]"
shipkit --help
```

Collector package (only needed if you run the API outside Docker Compose):

```bash
cd collector
python -m venv .venv
source .venv/Scripts/activate   # or .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

---

## 2. Quick check (no Docker)

```bash
cd examples/monorepo
# first time only: make it a git repo
git init -b main
git add .
git commit -m "feat: initial monorepo"

shipkit ci --all --dry-run
shipkit release --dry-run
```

`--dry-run` prints the plan and does not start containers or write release files.

---

## 3. Change-aware CI (needs Docker)

Start Docker Desktop, then from `examples/monorepo`:

```bash
# branch with only an API change
git checkout -b change-api
# edit services/api/... then:
git add -A && git commit -m "fix: api tweak"
shipkit ci --base main --dry-run   # should plan only api
shipkit ci --base main             # runs api tests in Docker
```

Useful flags:

| Command | Meaning |
|---|---|
| `shipkit ci` | Diff vs `main`, run affected services |
| `shipkit ci --base develop` | Diff vs another ref |
| `shipkit ci --dry-run` | Plan only |
| `shipkit ci --all` | Every service |
| `shipkit ci --max-workers 8` | Parallelism per layer |

---

## 4. Log collector (Docker Compose)

From the **repo root** (not `examples/monorepo`):

```bash
docker compose up --build -d   # detached; or omit -d to attach
```

Collector: http://localhost:8000  
Health: http://localhost:8000/health  

In another terminal (CLI venv activated):

```bash
# short-lived image that prints to stdout then exits
shipkit run demo hello-world
shipkit logs --service demo --since 1h
curl http://localhost:8000/health
```

Stop with `docker compose down`.

---

## 5. Releases

```bash
cd examples/monorepo
echo 0.1.0 > VERSION
git add VERSION && git commit -m "chore: add VERSION"
git tag v0.1.0
# add a few feat:/fix: commits, then:
shipkit release --dry-run
# shipkit release              # local: VERSION + CHANGELOG + commit + tag
# shipkit release --push --github   # needs origin + GITHUB_TOKEN
```

---

## 6. Run tests (dev)

```bash
cd cli && pytest -q && ruff check src tests
cd ../collector && pytest -q && ruff check app tests
```

---

## 7. GitHub Action

In a workflow of a monorepo that has `shipkit.yml`:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: your-org/shipkit@main
  with:
    base: main
    max-workers: "4"
```

See [README.md](README.md) for architecture and full feature docs, and [DEMO.md](DEMO.md) for a walkthrough / interview script.
