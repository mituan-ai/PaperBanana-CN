#!/usr/bin/env python3
"""Decide whether an MCP Registry version is new or identical."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0/servers"


def registered_versions(name: str) -> list[dict]:
    query = urllib.parse.urlencode({"search": name, "limit": 100})
    with urllib.request.urlopen(f"{REGISTRY_URL}?{query}", timeout=30) as response:
        payload = json.load(response)
    return [
        entry["server"]
        for entry in payload.get("servers", [])
        if entry.get("server", {}).get("name") == name
    ]


def write_publish_output(publish: bool) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    line = f"publish={'true' if publish else 'false'}\n"
    print(line, end="")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(line)


def comparable_registry_metadata(server: dict) -> dict:
    """Return fields retained by the MCP Registry read API."""
    comparable = dict(server)
    # The Registry accepts tool declarations during publication but omits them
    # from server records returned by its read API.
    comparable.pop("tools", None)
    return comparable


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("server.json"))
    args = parser.parse_args()

    local = json.loads(args.manifest.read_text(encoding="utf-8"))
    matches = [
        server
        for server in registered_versions(local["name"])
        if server.get("version") == local["version"]
    ]
    if not matches:
        print(f"{local['name']} {local['version']} is not present in the MCP Registry.")
        write_publish_output(True)
        return
    if len(matches) != 1 or comparable_registry_metadata(
        matches[0]
    ) != comparable_registry_metadata(local):
        raise RuntimeError(
            f"MCP Registry already contains {local['name']} {local['version']} "
            "with different metadata"
        )
    print(f"MCP Registry already contains identical metadata for {local['name']}.")
    write_publish_output(False)


if __name__ == "__main__":
    main()
