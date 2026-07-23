#!/usr/bin/env python3
"""Verify the installed PaperBanana-CN MCP server over stdio."""

from __future__ import annotations

import argparse
import asyncio

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

EXPECTED_TOOLS = {
    "batch_diagrams",
    "batch_plots",
    "continue_diagram",
    "continue_plot",
    "continue_run",
    "download_references",
    "evaluate_diagram",
    "evaluate_plot",
    "generate_diagram",
    "generate_plot",
    "orchestrate_figures",
}


async def check_server(command: str) -> None:
    transport = StdioTransport(command=command, args=["mcp"])
    async with Client(transport, timeout=30) as client:
        tools = await client.list_tools()
    actual = {tool.name for tool in tools}
    if actual != EXPECTED_TOOLS:
        missing = sorted(EXPECTED_TOOLS - actual)
        unexpected = sorted(actual - EXPECTED_TOOLS)
        raise RuntimeError(f"MCP tool mismatch: missing={missing}, unexpected={unexpected}")
    print(f"MCP stdio handshake passed with {len(actual)} tools.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--command",
        default="paperbanana-cn",
        help="Installed PaperBanana-CN executable to launch",
    )
    args = parser.parse_args()
    asyncio.run(check_server(args.command))


if __name__ == "__main__":
    main()
