from typing import Annotated

from fastapi import Body, Depends, Request, APIRouter

from app.agents.executor import run_agent
from app.middleware.auth import authenticate
from app.middleware.authorize import require_permission
from app.lib.response_formatter import success_response
from app.middleware.ratelimiter import chat_limiter

router = APIRouter(dependencies=[Depends(authenticate)])


@router.post(
    "/research",
    dependencies=[
        Depends(chat_limiter),
        Depends(require_permission("conversations:create")),
    ],
)
async def agent_research(
    question: Annotated[str, Body(embed=True)], request: Request
) -> dict[str, object]:
    """Assign a role to a user."""
    user_id = getattr(request.state, "user_id")
    correlation_id = getattr(request.state, "correlation_id")

    result = await run_agent(
        question=question,
        user_id=user_id,
        correlation_id=correlation_id,
    )

    return success_response(
        "Agent research completed successfully",
        {
            "answer": result["answer"],
            "sources": result["sources"],
            "confidence": result["confidence"],
            "metadata": {
                "iterations": result["iterations"],
                "cost_usd": result["total_cost_usd"],
                "termination_reason": result["termination_reason"],
            },
        },
    )
