import asyncio

from mcp import Client, StdioServerParameters
from server import server


async def assert_add_contract(client: Client) -> None:
    async with client:
        tools = await client.list_tools()
        assert [(tool.name, tool.input_schema) for tool in tools.tools] == [
            (
                "add",
                {
                    "properties": {
                        "a": {"title": "A", "type": "integer"},
                        "b": {"title": "B", "type": "integer"},
                    },
                    "required": ["a", "b"],
                    "title": "addArguments",
                    "type": "object",
                },
            )
        ]

        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.structured_content == {"result": 5}

        invalid = await client.call_tool("add", {"a": "two", "b": 3})
        assert invalid.is_error


def test_in_process_contract() -> None:
    asyncio.run(assert_add_contract(Client(server)))


def test_stdio_protocol() -> None:
    params = StdioServerParameters(
        command="uv",
        args=["run", "mcp", "run", "server.py:server"],
    )
    asyncio.run(assert_add_contract(Client(params)))
