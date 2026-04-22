from typing import Any

from app.lib.cache import cache_del
from app.lib.events import APP_EVENTS

from .admin import AdminEvents
from .document import DocEvents


@APP_EVENTS.on(AdminEvents.ROLE_ASSIGNED)
async def handle_role_assigned(**data: Any) -> None:
    """Handle role assigned event."""
    try:
        await cache_del(f"permissions:{data.get('target_user_id')}")
        print(f"Cache busted: permissions for {data.get('target_user_id')}")
    except Exception as e:
        print("Failed to bust permissions cache:", e)


@APP_EVENTS.on(AdminEvents.ROLE_REVOKED)
async def handle_role_revoked(**data: Any) -> None:
    """Handle role revoked event."""
    try:
        await cache_del(f"permissions:{data.get('target_user_id')}")
    except Exception as e:
        print("Failed to bust permissions cache:", e)


@APP_EVENTS.on(DocEvents.DOCUMENT_DELETED)
async def handle_document_deleted(**data: Any) -> None:
    """Handle document deleted event."""
    try:
        await cache_del(f"doc:{data.get('document_id')}")
    except Exception as e:
        print("Failed to bust document cache:", e)
