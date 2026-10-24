# shipkit-collector

FastAPI + PostgreSQL log collector for ShipKit.

Run with Docker Compose from the repo root (`docker compose up`),
or locally: `pip install -e ".[dev]"`, set
`SHIPKIT_COLLECTOR_DATABASE_URL`, run `alembic upgrade head`, then
`uvicorn app.main:app`. Full documentation is in the project
README at the repo root (`../README.md`).
