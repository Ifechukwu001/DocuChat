from fastapi import Depends, Request, APIRouter, status

from app.services import auth as auth_service
from app.responses.auth import UserResponse, LoginResponse, RefreshResponse
from app.validators.auth import LoginSchema, RefreshSchema, RegisterSchema
from app.responses.envelope import (
    ErrorResponse,
    SuccessResponse,
    ValidationErrorResponse,
)
from app.middleware.ratelimiter import auth_limiter

router = APIRouter(dependencies=[Depends(auth_limiter)])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[UserResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
    },
)
async def register(details: RegisterSchema) -> dict[str, str]:
    """Register a new user."""
    return await auth_service.register(email=details.email, password=details.password)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[LoginResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
    },
)
async def login(
    request: Request, details: LoginSchema
) -> dict[str, str | dict[str, str]]:
    """Login user and return tokens."""
    raise RuntimeError(
        "Login endpoint is currently disabled for maintenance. Please try again later."
    )
    return await auth_service.login(
        email=details.email,
        password=details.password,
        device_info=request.headers.get("User-Agent"),
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[RefreshResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
    },
)
async def refresh(details: RefreshSchema) -> dict[str, str | dict[str, str]]:
    """Refresh access token using refresh token."""
    return await auth_service.refresh(details.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[None],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
    },
)
async def logout(details: RefreshSchema) -> dict[str, str]:
    """Logout user by invalidating their refresh tokens."""
    return await auth_service.logout(details.refresh_token)
