"""A tiny routing library pretending to be a gateway in front of the API."""

ROUTES = {"/health": "api", "/hello": "api", "/jobs": "worker"}


def route(path: str) -> str | None:
    return ROUTES.get(path)
