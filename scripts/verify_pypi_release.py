#!/usr/bin/env python3
"""Decide whether a PyPI release is new or byte-identical to local artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def local_hashes(dist_dir: Path) -> dict[str, str]:
    artifacts = [*dist_dir.glob("*.whl"), *dist_dir.glob("*.tar.gz")]
    if not artifacts:
        raise RuntimeError(f"No wheel or sdist found in {dist_dir}")
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(artifacts)}


def remote_hashes(project: str, version: str) -> dict[str, str] | None:
    encoded_project = urllib.parse.quote(project)
    encoded_version = urllib.parse.quote(version)
    url = f"https://pypi.org/pypi/{encoded_project}/{encoded_version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    return {item["filename"]: item["digests"]["sha256"] for item in payload["urls"]}


def write_publish_output(publish: bool) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    line = f"publish={'true' if publish else 'false'}\n"
    print(line, end="")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()

    local = local_hashes(args.dist_dir)
    remote = remote_hashes(args.project, args.version)
    if remote is None:
        print(f"{args.project} {args.version} is not present on PyPI.")
        write_publish_output(True)
        return
    if remote != local:
        raise RuntimeError(
            f"PyPI already contains {args.project} {args.version} with different artifacts: "
            f"local={local}, remote={remote}"
        )
    print(f"PyPI already contains byte-identical artifacts for {args.project} {args.version}.")
    write_publish_output(False)


if __name__ == "__main__":
    main()
