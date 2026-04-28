from typing import Any
from datetime import UTC, datetime

from fastapi import Request, APIRouter
from tortoise import Tortoise

from app.lib.cache import cache_redis

router = APIRouter()


@router.get("/live")
async def health_live(request: Request) -> dict[str, Any]:
    """Liveness check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime": (datetime.now(UTC) - request.app.state.uptime).total_seconds(),
    }


@router.get("/ready")
async def health_ready() -> dict[str, Any]:
    """Readiness check endpoint."""
    checks: dict[str, dict[str, str]] = {}

    # Check database connection
    try:
        await Tortoise.get_connection("default").execute_query("SELECT 1")  # type: ignore
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}

    # Check Redis connection
    try:
        await cache_redis.ping()  # type: ignore
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)}

    all_healthy = all(check["status"] == "ok" for check in checks.values())

    return {
        "status": "ok" if all_healthy else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }
