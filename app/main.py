from contextlib import AsyncExitStack, asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.events.auth_events  # type: ignore  # noqa: F401
from app import __version__, __display_name__
from app.env import settings
from app.routes import router as api_router
from app.orm.config import register_orm


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(register_orm(app))

        yield


application = FastAPI(title=__display_name__, version=__version__, lifespan=_lifespan)


# Add CORS middleware
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

application.include_router(api_router, prefix="/api")


from app.error_handlers import *  # noqa: E402, F403
