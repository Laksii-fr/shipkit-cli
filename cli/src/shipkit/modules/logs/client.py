"""Querying the collector for `shipkit logs`."""

import httpx

from shipkit.core.errors import ShipkitError
from shipkit.modules.logs.models import LogRecord


class LogClient:
    def __init__(self, collector_url: str, client: httpx.Client | None = None) -> None:
        self._url = collector_url.rstrip("/")
        self._client = client or httpx.Client(timeout=30)
        self._owns_client = client is None

    def query(
        self,
        *,
        service: str | None = None,
        level: str | None = None,
        since: str | None = None,
        grep: str | None = None,
        limit: int = 200,
    ) -> list[LogRecord]:
        params: dict[str, object] = {"limit": limit}
        if service:
            params["service"] = service
        if level:
            params["level"] = level
        if since:
            params["since"] = since
        if grep:
            params["q"] = grep
        try:
            response = self._client.get(f"{self._url}/logs", params=params)
        except httpx.HTTPError as err:
            raise ShipkitError(
                f"Collector not reachable at {self._url}. "
                f"Start it with 'docker compose up' or pass --collector. ({err})"
            ) from err
        if response.status_code == 400:
            detail = response.json().get("detail", response.text[:200])
            raise ShipkitError(f"Collector rejected the query: {detail}")
        if response.status_code != 200:
            raise ShipkitError(
                f"Collector query failed with HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
        return [LogRecord.model_validate(row) for row in response.json()]

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
