from typing import Any

from .index import ToolDefination
from .final_answer import final_answer_tool
from .search_document import search_documents_tool

# Add more tools here as you build them
TOOL_REGISTRY: dict[str, ToolDefination] = {
    search_documents_tool["name"]: search_documents_tool,
    # Improve: "get_document_summary": document_summary_tool,
    # Improve: "analyze_chunks": analyze_chunks_tool,
    final_answer_tool["name"]: final_answer_tool,
}


#  Convert to OpenAI/Ollama function calling format
def get_tool_schemas() -> list[dict[str, Any]]:
    """Get the tool definitions in a format compatible with OpenAI/Ollama function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"].model_json_schema(
                    mode="serialization"
                ),
            },
        }
        for tool in TOOL_REGISTRY.values()
        if tool["name"] != "final_answer"
    ]
