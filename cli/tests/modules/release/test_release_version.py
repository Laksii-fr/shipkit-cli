"""Phase 4: semver parsing and bumping."""

import pytest

from shipkit.core.errors import ShipkitError
from shipkit.modules.release.version import SemVer


@pytest.mark.parametrize(
    "text,level,expected",
    [
        ("1.4.2", "major", "2.0.0"),
        ("1.4.2", "minor", "1.5.0"),
        ("1.4.2", "patch", "1.4.3"),
        ("v0.1.0", "minor", "0.2.0"),
        ("2.0.0", "major", "3.0.0"),
    ],
)
def test_bump(text, level, expected):
    assert str(SemVer.parse(text).bump(level)) == expected


def test_parse_strips_v_prefix():
    assert SemVer.parse("v1.2.3") == SemVer(1, 2, 3)


@pytest.mark.parametrize("bad", ["1.2", "a.b.c", "1.2.3.4", ""])
def test_parse_rejects_non_semver(bad):
    with pytest.raises(ShipkitError, match="Not a semantic version"):
        SemVer.parse(bad)
