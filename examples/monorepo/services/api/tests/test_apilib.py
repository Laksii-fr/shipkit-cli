import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from apilib import handle_request  # noqa: E402


def test_health():
    assert handle_request("/health")["status"] == 200


def test_not_found():
    assert handle_request("/missing")["status"] == 404
