"""MCP Registry metadata must match the installed server."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_server.server import mcp
from scripts.smoke_mcp import EXPECTED_TOOLS

ROOT = Path(__file__).resolve().parents[1]


async def test_registry_manifest_matches_runtime_tools_and_distribution():
    manifest = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    runtime_tools = {tool.name for tool in await mcp.list_tools()}
    declared_tools = {tool["name"] for tool in manifest["tools"]}
    package = manifest["packages"][0]

    assert manifest["name"] == "io.github.mituan-ai/paperbanana-cn"
    assert manifest["version"] == "2.0.1"
    assert runtime_tools == declared_tools == EXPECTED_TOOLS
    assert package["identifier"] == "paperbanana-cn"
    assert package["version"] == manifest["version"]
    assert package["runtimeHint"] == "uvx"
    assert package["packageArguments"] == [{"type": "positional", "value": "mcp"}]
    assert package["transport"] == {"type": "stdio"}
