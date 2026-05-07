from uuid import UUID

from pydantic import Field, create_model

from app.services.search import semantic_search

from .index import ToolResult, ToolContext, ToolDefination


async def _semantic_search_tool_handler(
    context: ToolContext | None,
    query: str,
    document_id: UUID | None = None,
    top_k: int = 5,
) -> ToolResult:
    """Handler for the search_documents tool, performing a semantic search."""
    if context is None:
        return {
            "success": False,
            "data": "Context is required for this tool",
        }

    results = await semantic_search(
        query=query,
        user_id=context["user_id"],
        document_id=document_id,
        top_k=top_k,
        correlation_id=context["correlation_id"],
    )
    return {
        "success": True,
        "data": {
            "results": [
                {
                    "document": r.document.title,
                    "content": r.content,
                    "score": r.score,
                }
                for r in results
            ],
            "totalResults": len(results),
        },
    }


search_documents_tool: ToolDefination = {
    "name": "search_documents",
    "description": (
        "Search across the user's uploaded documents for information "
        "relevant to a specific query. Returns the most relevant text "
        "passages with similarity scores."
    ),
    "parameters": create_model(
        "SearchDocumentsParams",
        query=(
            str,
            Field(
                min_length=3,
                max_length=500,
                description="The search query describing what to look for",
            ),
        ),
        document_id=(
            UUID | None,
            Field(None, description="Optional: search within a specific document"),
        ),
        top_k=(int, Field(5, ge=1, le=10, description="Number of results to return")),
    ),
    "handler": _semantic_search_tool_handler,
}
