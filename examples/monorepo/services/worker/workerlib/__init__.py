"""A tiny background-job library pretending to be a worker service."""


def run_job(payload: dict) -> dict:
    kind = payload.get("kind")
    if kind == "email":
        return {"done": True, "sent_to": payload.get("to", "")}
    if kind == "resize":
        return {"done": True, "size": payload.get("size", 0)}
    return {"done": False, "error": f"unknown job kind: {kind}"}
