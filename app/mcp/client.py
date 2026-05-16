from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from app.lib.logging import logger


def create_mcp_client(server_url: str) -> Client[StreamableHttpTransport]:
    """Factory to create an MCP client connected to the given server URL."""
    transport = StreamableHttpTransport(url=server_url)

    client = Client(transport=transport)

    return client


async def discover_external_tools(server_url: str) -> list[dict[str, Any]]:
    """Discover available tools from the MCP server."""
    client = create_mcp_client(server_url)

    try:
        tools = await client.list_tools()

        logger.info(
            "Discovered MCP tools",
            server=server_url,
            tool_count=len(tools),
            tools=[t.name for t in tools],
        )

        # Convert MCP tool schemas to OpenAI function format
        # so our agent executor can use them
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
                # Store reference for execution
                "_mcp_client": client,
                "_mcp_tool_name": tool.name,
            }
            for tool in tools
        ]
    except Exception as e:
        logger.error("Failed to discover MCP tools", server=server_url, error=str(e))
        return []


async def call_external_tool(
    client: Client[StreamableHttpTransport], tool_name: str, **args: Any
) -> Any:
    """Call a specific tool on the MCP server with given arguments."""
    result = await client.call_tool(name=tool_name, arguments=args)
    logger.info(
        "Called MCP tool",
        tool=tool_name,
        arguments=args,
        result=str(result)[:200],  # Log a snippet of the result
    )

    # Extract text content from MCP response
    text_content = "\n".join(*[c.text for c in result.content if c.type == "text"])
    return text_content
