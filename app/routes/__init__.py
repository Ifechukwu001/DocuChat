from fastapi import APIRouter

from . import auth, admin, documents, conversations

router = APIRouter()
_router_v1 = APIRouter(prefix="/v1")


_router_v1.include_router(auth.router, prefix="/auth", tags=["Authentication"])
_router_v1.include_router(admin.router, prefix="/admin", tags=["Admin"])
_router_v1.include_router(documents.router, prefix="/documents", tags=["Documents"])
_router_v1.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations"]
)

router.include_router(_router_v1)
