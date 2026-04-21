import hmac
import secrets
from collections.abc import Callable, Awaitable

from fastapi import Request

from app.lib.exceptions import ErrorResponse


def verify_webhook_signature(
    secret: str, header_name: str
) -> Callable[[Request], Awaitable[None]]:
    async def _(request: Request):
        signature = str(request.headers.get(header_name.lower()))

        if not signature:
            raise ErrorResponse(status=401, message="Missing signature header")

        raw_body = await request.body()

        expected_signature = hmac.new(secret.encode(), raw_body, "sha256").hexdigest()

        if not secrets.compare_digest(signature, expected_signature):
            raise ErrorResponse(status=401, message="Invalid signature")

    return _
