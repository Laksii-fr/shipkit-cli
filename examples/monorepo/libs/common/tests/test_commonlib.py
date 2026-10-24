import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from commonlib import clamp, slugify  # noqa: E402


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  many   spaces ") == "many-spaces"


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(99, 0, 10) == 10
