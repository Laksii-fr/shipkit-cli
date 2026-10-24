"""A tiny request-handling library pretending to be an API service."""


def handle_request(path: str) -> dict:
    if path == "/health":
        return {"status": 200, "body": {"ok": True}}
    if path == "/hello":
        return {"status": 200, "body": {"message": "hello"}}
    return {"status": 404, "body": {"error": "not found"}}

