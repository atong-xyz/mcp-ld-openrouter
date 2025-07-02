from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack
from openai import OpenAI
import json, os, asyncio
from typing import Optional
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.messages = []

    async def connect_to_server(self, server_config):
        # ⬇️ MCP Server connection (stdio-based)
        server_params = StdioServerParameters(**server_config)
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        # ⬇️ MCP Client session begins
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # ⬇️ MCP tools discovered here
        tools = await self.session.list_tools()
        print("Tools:", [t.name for t in tools.tools])

    def format_tools(self, tools):
        # Convert tool metadata into OpenAI-compatible format for tool calling
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.inputSchema["properties"],
                        "required": tool.inputSchema.get("required", [])
                    }
                }
            } for tool in tools
        ]

    async def process_query(self, query: str):
        self.messages.append({"role": "user", "content": query})

        # Refresh tools list from MCP server
        tools = await self.session.list_tools()
        formatted_tools = self.format_tools(tools.tools)

        # Ask OpenRouter model for a response
        completion = self.openai.chat.completions.create(
            model=os.getenv("MODEL"),
            tools=formatted_tools,
            messages=self.messages
        )
        message = completion.choices[0].message
        self.messages.append(message.model_dump())

        if message.tool_calls:
            call = message.tool_calls[0]
            args = json.loads(call.function.arguments or "{}")

            # ⬇️ MCP tool execution (calls your MCP server with given tool and args)
            result = await self.session.call_tool(call.function.name, args)

            self.messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": result.content
            })

            # Follow-up completion to generate response with tool result
            followup = self.openai.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=self.messages
            )
            return followup.choices[0].message.content
        else:
            return message.content

    async def chat_loop(self):
        while True:
            query = input("\nAsk: ")
            if query.lower() == "quit":
                break
            response = await self.process_query(query)
            print("\nResponse:\n", response)

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    # ⚙️ SERVER_CONFIG: Choose your MCP server setup here

    # ✅ SCENARIO A: If a native MCP server package is available (e.g., LaunchDarkly)
    SERVER_CONFIG = {
        "command": "npx",
        "args": [
            "-y", "--package", "@launchdarkly/mcp-server", "--", "mcp", "start",
            "--api-key", os.getenv("LD_API_KEY")
        ]
    }

    # 🛠️ SCENARIO B: If no MCP server exists but there's a REST API:
    # You would instead write a custom MCP server in Node.js or Python that:
    #  - Exposes tools in MCP-compatible format
    #  - Handles stdio or HTTP requests from MCPClient
    #  - Internally performs HTTP requests to the 3rd-party REST API
    # Example (pseudo-code):
    #
    # SERVER_CONFIG = {
    #     "command": "python",
    #     "args": ["./my_custom_mcp_server.py"]  # this file wraps your REST API
    # }

    client = MCPClient()
    try:
        await client.connect_to_server(SERVER_CONFIG)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
