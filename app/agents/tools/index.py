from uuid import UUID
from typing import Any, TypedDict, Concatenate, NotRequired
from collections.abc import Callable, Awaitable

from pydantic import BaseModel


class ToolDefination(TypedDict):
    """Definition of a tool that an agent can use."""

    name: str
    description: str
    parameters: type[BaseModel]
    handler: Callable[Concatenate[ToolContext | None, ...], Awaitable[ToolResult]]


class ToolContext(TypedDict):
    """Context passed to a tool when it's invoked by an agent."""

    user_id: UUID
    correlation_id: str


class ToolResult(TypedDict):
    """Result returned by a tool after execution."""

    success: bool
    data: Any
    token_cost: NotRequired[float]
