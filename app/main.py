from datetime import UTC, datetime
from contextlib import AsyncExitStack, asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__, __description__, __display_name__
from app.env import settings
from app.routes import router as api_router
from app.orm.config import register_orm


@asynccontextmanager
async def _lifespan(api: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as stack:
        import app.events  # type: ignore
        import app.queues  # type: ignore  # noqa: F401

        await stack.enter_async_context(register_orm(api))
        yield


application = FastAPI(
    lifespan=_lifespan,
    version=__version__,
    title=__display_name__,
    description=__description__,
    docs_url="/api-docs",
    openapi_url="/api-docs.json",
)


# Add CORS middleware
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@application.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


application.include_router(api_router, prefix="/api")


from app.error_handlers import *  # noqa: E402, F403
