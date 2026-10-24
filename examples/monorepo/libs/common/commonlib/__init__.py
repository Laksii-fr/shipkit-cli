"""Shared helpers used across the demo monorepo."""


def slugify(text: str) -> str:
    """Lowercase, trimmed, spaces and underscores become hyphens."""
    cleaned = "".join(ch if ch.isalnum() or ch in " -_" else "" for ch in text.lower())
    return "-".join(cleaned.replace("_", " ").split())


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))
