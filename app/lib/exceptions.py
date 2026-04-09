class ErrorResponse(Exception):
    """API Error Response Exception."""

    def __init__(self, status: int, message: str) -> None:
        """Initializes the Error Response."""
        self.status = status
        self.message = message
