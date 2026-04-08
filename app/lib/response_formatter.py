from typing import Any

from app.lib.exceptions import ErrorResponse


def success_response(
    status_code: int,
    message: str,
    data: Any = None,  # noqa: ANN401
) -> dict[str, Any]:
    """Returns a response for success responses."""
    return {
        "status": "success",
        "status_code": status_code,
        "message": message,
        "data": data,
    }


def error_response(
    status_code: int, message: str, errors: list[str] | None = None
) -> dict[str, Any]:
    """Response for failure responses.

    Raises:
        ErrorResponse: Custom HTTP Error.
    """
    raise ErrorResponse(status_code, message, errors)
