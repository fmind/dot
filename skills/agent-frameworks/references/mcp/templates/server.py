"""<description>."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from importlib.metadata import version

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

__version__ = version("<slug>")

server = MCPServer("<slug>", version=__version__)


@server.tool(
    name="<package>_add",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def add(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


def build_parser() -> argparse.ArgumentParser:
    """Define CLI flags so `--help` and `--version` stay free of side effects."""
    parser = argparse.ArgumentParser(
        prog="<slug>", description="<description>.", allow_abbrev=False, suggest_on_error=True
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport protocol",
    )
    parser.add_argument("--host", default=None, help="Bind host for streamable-http (default: HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Bind port for streamable-http (default: PORT or 8000)")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entrypoint invoked by the `<slug>` console script or `uv run`."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.transport == "streamable-http":
        host = (args.host or os.environ.get("HOST") or "127.0.0.1").strip().lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            sys.stderr.write("Error: refusing non-loopback bind without auth and explicit TransportSecuritySettings.\n")
            raise SystemExit(1)
        try:
            port = args.port if args.port is not None else int(os.environ.get("PORT") or "8000")
        except ValueError as error:
            sys.stderr.write("Error: invalid PORT environment variable.\n")
            raise SystemExit(1) from error
        if not 1 <= port <= 65535:
            sys.stderr.write("Error: invalid PORT environment variable (must be 1-65535).\n")
            raise SystemExit(1)
        # mcp>=2.3.0 enables loopback TransportSecuritySettings Host/Origin DNS-rebinding checks for
        # 127.0.0.1, localhost, and ::1. Before removing the loopback guard above for hosted deploys,
        # configure TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=[...],
        # allowed_origins=[...]) and enforce OAuth or workload identity.
        server.run(transport="streamable-http", host=host, port=port, stateless_http=True)
    else:
        server.run(transport="stdio")
