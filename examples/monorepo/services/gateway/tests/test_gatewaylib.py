import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from gatewaylib import route  # noqa: E402


def test_known_route():
    assert route("/health") == "api"


def test_unknown_route():
    assert route("/nope") is None
