from fastapi import Request, APIRouter, status

from app.services import auth as auth_service

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: Request) -> dict[str, str]:
    """Register a new user."""
    return await auth_service.register(**await request.json())


@router.post("/login")
async def login(request: Request) -> dict[str, str | dict[str, str]]:
    """Login user and return tokens."""
    return await auth_service.login(
        **await request.json(), device_info=request.headers.get("User-Agent")
    )


@router.post("/refresh")
async def refresh(request: Request) -> dict[str, str | dict[str, str]]:
    """Refresh access token using refresh token."""
    return await auth_service.refresh((await request.json())["refresh_token"])


@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    """Logout user by invalidating their refresh tokens."""
    await auth_service.logout((await request.json())["refresh_token"])
    return {"message": "Logged out"}
