"""Phase 6: shipper batching and client query params (httpx MockTransport)."""

import json
from datetime import UTC, datetime

import httpx
import pytest

from shipkit.core.errors import ShipkitError
from shipkit.modules.logs.client import LogClient
from shipkit.modules.logs.models import LogLine
from shipkit.modules.logs.shipper import LogShipper


def make_line(i: int) -> LogLine:
    return LogLine(service="api", ts=datetime.now(UTC), level="info", message=f"line {i}")


def test_shipper_flushes_at_batch_size_and_on_close():
    batches: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        batches.append(len(payload["lines"]))
        return httpx.Response(202, json={"accepted": len(payload["lines"])})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    shipper = LogShipper("http://collector", batch_size=3, client=client)
    for i in range(7):
        shipper.add(make_line(i))
    assert batches == [3, 3]
    shipper.close()
    assert batches == [3, 3, 1]
    assert shipper.shipped == 7


def test_shipper_unreachable_collector_is_clear_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    shipper = LogShipper("http://collector", batch_size=1, client=client)
    with pytest.raises(ShipkitError, match="Collector not reachable"):
        shipper.add(make_line(1))


def test_client_builds_query_params():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "service": "api",
                    "ts": "2026-10-24T10:00:00",
                    "level": "error",
                    "message": "timeout",
                }
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    records = LogClient("http://collector", client=client).query(
        service="api", level="error", since="1h", grep="timeout"
    )
    assert seen["params"] == {
        "limit": "200",
        "service": "api",
        "level": "error",
        "since": "1h",
        "q": "timeout",
    }
    assert records[0].message == "timeout"


def test_client_400_is_clear_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "Invalid since value"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ShipkitError, match="Invalid since"):
        LogClient("http://collector", client=client).query(since="bogus")
