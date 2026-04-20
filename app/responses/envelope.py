from pydantic import BaseModel


class SuccessResponse[T](BaseModel):
    """Success Response."""

    success: bool
    message: str
    data: T | None = None


class ErrorResponse(BaseModel):
    """Error Response."""

    success: bool
    message: str


class ValidationErrorResponse(BaseModel):
    """Validation Error Response."""

    success: bool
    message: str
    errors: list[str]


class _PaginationMetadata(BaseModel):
    page: int
    limit: int
    total: int


class PaginatedSuccessResponse[T](BaseModel):
    """Paginated Response."""

    success: bool
    message: str
    metadata: _PaginationMetadata
    data: list[T]


class _OffsetMetadata(BaseModel):
    offset: int
    limit: int
    total: int
    count: int


class OffsetSuccessResponse[T](BaseModel):
    """Offset Response."""

    success: bool
    message: str
    metadata: _OffsetMetadata
    data: list[T]
