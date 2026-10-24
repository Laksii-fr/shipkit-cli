"""Semantic version parsing and bumping."""

import re
from dataclasses import dataclass

from shipkit.core.errors import ShipkitError

_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> "SemVer":
        match = _PATTERN.match(text.strip())
        if not match:
            raise ShipkitError(f"Not a semantic version: '{text}' (expected e.g. 1.4.2)")
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    def bump(self, level: str) -> "SemVer":
        if level == "major":
            return SemVer(self.major + 1, 0, 0)
        if level == "minor":
            return SemVer(self.major, self.minor + 1, 0)
        if level == "patch":
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ShipkitError(f"Unknown bump level: '{level}' (major, minor or patch)")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
