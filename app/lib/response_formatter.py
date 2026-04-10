from typing import Any

from app.lib.exceptions import ErrorResponse


def success_response(
    message: str,
    data: Any = None,  # noqa: ANN401
) -> dict[str, Any]:
    """Returns a response for success responses."""
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(status_code: int, message: str) -> dict[str, Any]:
    """Response for failure responses.

    Raises:
        ErrorResponse: Custom HTTP Error.
    """
    raise ErrorResponse(status_code, message)
