import json
from uuid import UUID
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field
from mcp.types import TextContent
from fastmcp.tools import ToolResult
from fastmcp.prompts import Message, PromptResult
from fastmcp.resources import ResourceResult, ResourceContent

from app.orm.models import Document
from app.lib.logging import logger
from app.services.search import semantic_search
from app.lib.response_formatter import error_response

mcp_server = FastMCP(name="docuchat")


@mcp_server.tool()
async def search_documents(
    query: Annotated[str, Field(min_length=3, description="What to search for")],
    document_id: Annotated[
        UUID | None,
        Field(None, description="Optional: limit search to a specific document"),
    ],
    top_k: Annotated[
        int, Field(5, ge=1, le=10, description="Number of results to return")
    ],
) -> ToolResult:
    """Search across uploaded documents for information relevant to a query.

    Returns the most relevant text passages with similarity scores.
    """
    user_id = get_current_user_id()

    results = await semantic_search(query, user_id, document_id, top_k)

    logger.info("MCP tool: search_documents", query=query[:100], results=len(results))

    return ToolResult(
        content=TextContent(
            type="text",
            text=json.dumps(
                {
                    "results": [
                        {
                            "document": r.document.title,
                            "content": r.content,
                            "score": round(r.score, 4),
                            "chunk_index": r.index,
                        }
                        for r in results
                    ],
                    "total_results": len(results),
                }
            ),
        )
    )


@mcp_server.tool()
async def list_documents() -> ToolResult:
    """List all uploaded documents with their processing status."""
    user_id = get_current_user_id()

    docs = (
        await Document.filter(user_id=user_id, deleted_at__isnull=True)
        .order_by("-created_at")
        .only("id", "title", "status", "chunk_count", "created_at")
        .all()
    )

    logger.info("MCP tool: search_documents", docs=len(docs))

    return ToolResult(
        content=TextContent(
            type="text",
            text=json.dumps(
                [
                    {
                        "id": d.id,
                        "title": d.title,
                        "status": d.status,
                        "chunk_count": d.chunk_count,
                        "created_at": d.created_at.isoformat(),
                    }
                    for d in docs
                ]
            ),
        )
    )


@mcp_server.resource("docuchat://documents/{document_id}/content")
async def document_content(document_id: UUID) -> ResourceResult:
    """Fetch document."""
    user_id = get_current_user_id()
    doc = (
        await Document.filter(
            id=document_id, user_id=user_id, deleted_at__isnull=True, status="ready"
        )
        .only("user_id", "title", "content")
        .first()
    )

    if not doc:
        error_response(404, "Document not found")

    return ResourceResult(
        contents=[
            ResourceContent(
                content=json.dumps({"name": doc.title, "content": doc.content}),
                mime_type="application/json",
            )
        ]
    )


@mcp_server.prompt()
async def research_query(
    topic: Annotated[str, Field(description="The topic to research")],
) -> PromptResult:
    """Research a topic across uploaded documents."""
    return PromptResult(
        messages=[
            Message(
                role="user",
                content=TextContent(
                    type="text",
                    text="\n".join(
                        *[
                            "Please research the following topic across my uploaded documents:",
                            "",
                            f"Topic: {topic}",
                            "",
                            "Use the search_documents tool to find relevant information.",
                            "Synthesize the findings and cite which documents you found ",
                        ]
                    ),
                ),
            )
        ]
    )


def get_current_user_id() -> UUID:
    """Helper to get current user ID from MCP context."""
    # In a real implementation, this would extract user info from the request context,
    # such as an auth token. Here we return a fixed UUID for demonstration.
    return UUID("123e4567-e89b-12d3-a456-426614174000")
