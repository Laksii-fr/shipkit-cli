"""Creating a GitHub release through the REST API (httpx)."""

import httpx

from shipkit.core.errors import ShipkitError

_API = "https://api.github.com"


def create_release(
    *,
    owner: str,
    repo: str,
    tag: str,
    name: str,
    body: str,
    token: str,
    client: httpx.Client | None = None,
) -> str:
    """Create the release and return its html_url."""
    owns_client = client is None
    http = client or httpx.Client(timeout=30)
    try:
        response = http.post(
            f"{_API}/repos/{owner}/{repo}/releases",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"tag_name": tag, "name": name, "body": body},
        )
    except httpx.HTTPError as err:
        raise ShipkitError(f"Could not reach the GitHub API: {err}") from err
    finally:
        if owns_client:
            http.close()
    if response.status_code not in (200, 201):
        raise ShipkitError(
            f"GitHub release failed with HTTP {response.status_code}: {response.text[:200]}"
        )
    return str(response.json().get("html_url", ""))
