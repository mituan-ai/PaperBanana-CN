#!/usr/bin/env python3
"""Deterministic paperbanana-cn shim used by the composite Action smoke test."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image


def value_after(args: list[str], flag: str, default: str = "") -> str:
    try:
        return args[args.index(flag) + 1]
    except (ValueError, IndexError):
        return default


def record(args: list[str]) -> None:
    log_path = os.environ.get("FAKE_ACTION_LOG")
    if log_path:
        with Path(log_path).open("a", encoding="utf-8") as handle:
            handle.write(" ".join(args) + "\n")


def generate(args: list[str]) -> None:
    output_dir = Path(value_after(args, "--output-dir"))
    output_format = value_after(args, "--format", "png")
    extension = "jpg" if output_format == "jpeg" else output_format
    run_dir = output_dir / "run_fake_action"
    run_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 360), "#eef1f0").save(
        run_dir / f"final_output.{extension}",
        format="JPEG" if extension == "jpg" else "PNG",
    )


def main() -> None:
    args = sys.argv[1:]
    record(args)
    if not args:
        raise SystemExit("missing command")
    if args[0] == "connections" and args[1:2] == ["add"]:
        return
    if args[0] == "generate":
        generate(args)
        return
    raise SystemExit(f"unsupported fake command: {args}")


if __name__ == "__main__":
    main()
