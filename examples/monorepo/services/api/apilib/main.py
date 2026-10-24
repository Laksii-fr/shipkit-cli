"""Production wiring example: the API uses the shared common library.

Run from the monorepo root with:
    PYTHONPATH=libs/common:services/api python -m apilib.main
"""

from commonlib import slugify

from apilib import handle_request


def article_path(title: str) -> str:
    return f"/articles/{slugify(title)}"


if __name__ == "__main__":
    print(handle_request("/health"))
    print(article_path("ShipKit Demo Article"))
