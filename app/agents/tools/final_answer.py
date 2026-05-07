from typing import Literal

from pydantic import Field, create_model

from .index import ToolResult, ToolContext, ToolDefination


async def _final_answer_tool_handler(
    context: ToolContext | None,
    answer: str,
    sources: list[str],
    confidence: Literal["high", "medium", "low"],
) -> ToolResult:
    """Handler for the final_answer tool, providing the final answer to the user's question."""
    return {
        "success": True,
        "data": {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
        },
    }


final_answer_tool: ToolDefination = {
    "name": "final_answer",
    "description": (
        "Provide the final answer to the user's question. "
        "Call this when you have gathered enough information."
    ),
    "parameters": create_model(
        "FinalAnswerParams",
        answer=(
            str,
            Field(
                min_length=1, description="The complete answer to the user's question"
            ),
        ),
        sources=(
            list[str],
            Field(description="List of document names used as sources"),
        ),
        confidence=(
            Literal["high", "medium", "low"],
            Field(description="How confident you are in the answer"),
        ),
        context=(
            None,
            Field(None, description="Ignore and just pass None for this parameter"),
        ),
    ),
    "handler": _final_answer_tool_handler,
}
