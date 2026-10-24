import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from workerlib import run_job  # noqa: E402


def test_email_job():
    assert run_job({"kind": "email", "to": "a@example.com"})["done"] is True


def test_unknown_job():
    assert run_job({"kind": "teleport"})["done"] is False
