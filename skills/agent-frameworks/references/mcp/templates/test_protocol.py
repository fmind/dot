from __future__ import annotations

import asyncio
import subprocess
import sys

import pytest
from mcp import Client, StdioServerParameters

from <package> import __main__ as module_entrypoint
from <package> import __version__
from <package>.server import main, server


async def assert_add_contract(client: Client) -> None:
    async with client:
        tools = await client.list_tools()
        assert [(tool.name, tool.input_schema) for tool in tools.tools] == [
            (
                "<package>_add",
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

        result = await client.call_tool("<package>_add", {"a": 2, "b": 3})
        assert result.structured_content == {"result": 5}

        invalid = await client.call_tool("<package>_add", {"a": "two", "b": 3})
        assert invalid.is_error


def test_in_process_contract() -> None:
    asyncio.run(assert_add_contract(Client(server)))


def test_stdio_protocol() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "<package>"])
    asyncio.run(assert_add_contract(Client(params)))


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], ("stdio", {})),
        (
            ["--transport", "streamable-http", "--host", "::1", "--port", "9000"],
            ("streamable-http", {"host": "::1", "port": 9000, "stateless_http": True}),
        ),
    ],
)
def test_cli_transport_selection(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], expected: tuple[str, dict[str, object]]
) -> None:
    seen: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(server, "run", lambda *, transport="stdio", **kwargs: seen.append((transport, kwargs)))

    main(argv)

    assert seen == [expected]


def test_http_env_defaults_and_invalid_port(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(server, "run", lambda *, transport="stdio", **kwargs: seen.append((transport, kwargs)))
    monkeypatch.setenv("HOST", "::1")
    monkeypatch.setenv("PORT", "8080")
    main(["--transport", "streamable-http"])
    assert seen == [("streamable-http", {"host": "::1", "port": 8080, "stateless_http": True})]

    monkeypatch.setenv("PORT", "not-an-int")
    with pytest.raises(SystemExit) as raised:
        main(["--transport", "streamable-http"])
    assert raised.value.code == 1
    assert "Error: invalid PORT" in capsys.readouterr().err


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == f"{__version__}\n"


def test_module_entrypoint() -> None:
    assert module_entrypoint.__name__.endswith(".__main__")
    result = subprocess.run(
        [sys.executable, "-m", "<package>", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{__version__}\n"
    assert result.stderr == ""
