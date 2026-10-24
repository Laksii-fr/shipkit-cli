"""Buffering and batch-sending log lines to the collector.

One HTTP request per line would be far too slow, so lines are
buffered and flushed in batches of `batch_size`, and once more
on close().
"""

import httpx

from shipkit.core.errors import ShipkitError
from shipkit.modules.logs.models import LogLine

DEFAULT_BATCH_SIZE = 50


class LogShipper:
    def __init__(
        self,
        collector_url: str,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = collector_url.rstrip("/")
        self._batch_size = batch_size
        self._client = client or httpx.Client(timeout=30)
        self._owns_client = client is None
        self._buffer: list[LogLine] = []
        self.shipped = 0

    def add(self, line: LogLine) -> None:
        self._buffer.append(line)
        if len(self._buffer) >= self._batch_size:
            self.flush()

    def flush(self) -> int:
        if not self._buffer:
            return 0
        payload = {"lines": [line.model_dump(mode="json") for line in self._buffer]}
        try:
            response = self._client.post(f"{self._url}/ingest", json=payload)
        except httpx.HTTPError as err:
            raise ShipkitError(
                f"Collector not reachable at {self._url}. "
                f"Start it with 'docker compose up' or pass --collector. ({err})"
            ) from err
        if response.status_code != 202:
            raise ShipkitError(
                f"Collector rejected the batch with HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
        count = len(self._buffer)
        self._buffer = []
        self.shipped += count
        return count

    def close(self) -> None:
        try:
            self.flush()
        finally:
            if self._owns_client:
                self._client.close()

    def __enter__(self) -> "LogShipper":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
