from datetime import UTC, datetime
from contextlib import AsyncExitStack, asynccontextmanager
from collections.abc import Callable, Awaitable, AsyncIterator

from secure import Secure, ContentSecurityPolicy
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app import __version__, __description__, __display_name__
from app.env import settings
from app.routes import router as api_router
from app.orm.config import register_orm


@asynccontextmanager
async def _lifespan(api: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(register_orm(api))

        import app.events  # type: ignore
        import app.queues.workers  # type: ignore  # noqa: F401

        yield


application = FastAPI(
    lifespan=_lifespan,
    version=__version__,
    title=__display_name__,
    description=__description__,
    docs_url="/api-docs",
    openapi_url="/api-docs.json",
)


secure_headers = Secure.with_default_headers()
docs_secure_headers = Secure(
    csp=(
        ContentSecurityPolicy()
        .default_src("'self'")
        .script_src("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
        .style_src("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
        .img_src("'self'", "data:", "fastapi.tiangolo.com")
    )
)


@application.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware to add security headers to all responses."""
    response = await call_next(request)
    if request.url.path.startswith("/api-docs"):
        await docs_secure_headers.set_headers_async(response)
    else:
        await secure_headers.set_headers_async(response)
    return response


# Add CORS middleware
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight requests for 24 hours
)


@application.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


application.include_router(api_router, prefix="/api")


from app.error_handlers import *  # noqa: E402, F403
