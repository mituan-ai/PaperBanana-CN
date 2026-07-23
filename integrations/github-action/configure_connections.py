#!/usr/bin/env python3
"""Create the two temporary connection profiles used by the composite action."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    return value


def _connection_command(
    env: Mapping[str, str],
    *,
    role: str,
    prefix: str,
    key_env: str,
) -> list[str]:
    command = [
        "paperbanana-cn",
        "connections",
        "add",
        "--role",
        role,
        "--name",
        f"GitHub Action {role.title()}",
        "--provider",
        _required(env, f"{prefix}_PROVIDER"),
        "--model",
        _required(env, f"{prefix}_MODEL"),
        "--api-key-env",
        key_env,
    ]
    base_url = env.get(f"{prefix}_BASE_URL", "").strip()
    if base_url:
        command.extend(["--base-url", base_url])
    if role == "image":
        command.extend(["--size-mode", _required(env, "PB_IMAGE_SIZE_MODE")])
    return command


def configure_connections(env: Mapping[str, str]) -> None:
    _required(env, "PB_VLM_API_KEY")
    _required(env, "PB_IMAGE_API_KEY")
    commands = [
        _connection_command(env, role="vlm", prefix="PB_VLM", key_env="PB_VLM_API_KEY"),
        _connection_command(
            env,
            role="image",
            prefix="PB_IMAGE",
            key_env="PB_IMAGE_API_KEY",
        ),
    ]
    for command in commands:
        subprocess.run(command, check=True, env=dict(env))


def main() -> None:
    configure_connections(os.environ)


if __name__ == "__main__":
    main()
