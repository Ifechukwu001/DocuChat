import hashlib

from fastapi import Request


def attach_fingerprint(request: Request) -> None:
    """Generates a fingerprint for the incoming request based on various headers and the client's IP address."""
    signals = [
        request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else ""
        )
        .split(",")[0]
        .strip(),
        request.headers.get("User-Agent", ""),
        request.headers.get("Accept-Language", ""),
        request.headers.get("Accept-Encoding", ""),
    ]

    fingerprint = hashlib.sha256("|".join(signals).encode()).hexdigest()[:16]

    request.state.fingerprint = fingerprint
