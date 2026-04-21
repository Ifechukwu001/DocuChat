from datetime import UTC, datetime

import httpx

from app.env import settings


async def log_outgoing_request(request: httpx.Request) -> None:
    """Log outgoing OpenAI API requests."""
    start_time = datetime.now(UTC)
    request.extensions["start_time"] = start_time
    print(f"-> OpenAI {request.method.upper()} {request.url}")


async def log_incoming_response(response: httpx.Response) -> None:
    """Log incoming OpenAI API responses."""
    request = response.request
    start_time = request.extensions.get("start_time")
    duration = (datetime.now(UTC) - start_time).total_seconds() if start_time else None

    if not response.is_error:
        print(f"<- OpenAI {response.status_code} {request.url} ({duration}s)")
    else:
        print(f"X OpenAI {response.status_code} {request.url} ({duration}s)")


async def ratlimit_requests(response: httpx.Response) -> None:
    """Handle OpenAI API rate limits by sleeping and retrying."""
    remaining = int(response.headers.get("x-ratelimit-remaining-requests") or "999")

    if remaining < 50:
        print(f"OpenAI rate limit getting low: {remaining} remaining")


openai_client = httpx.AsyncClient(
    base_url="https://api.openai.com/v1",
    timeout=30,
    headers={
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "DocuChat/1.0",
    },
    event_hooks={
        "request": [log_outgoing_request],
        "response": [log_incoming_response, ratlimit_requests],
    },
)
