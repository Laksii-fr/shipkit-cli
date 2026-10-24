"""Shared error type for user-facing failures.

Controllers raise ShipkitError with a message written for the user.
Command files catch it, print it, and exit non-zero, so users never
see a stack trace for an expected failure (bad config, no git repo,
Docker down, and so on).
"""


class ShipkitError(Exception):
    """An expected, user-facing error."""
