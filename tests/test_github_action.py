"""GitHub Action wiring for independent, secret-safe connection profiles."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION_DIR = ROOT / "integrations" / "github-action"
_SPEC = importlib.util.spec_from_file_location(
    "paperbanana_action_connections",
    ACTION_DIR / "configure_connections.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Unable to load the GitHub Action connection helper")
_CONNECTION_HELPER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CONNECTION_HELPER)


def test_action_metadata_exposes_independent_connections_and_size_controls():
    action = yaml.safe_load((ACTION_DIR / "action.yml").read_text(encoding="utf-8"))
    inputs = action["inputs"]

    assert action["author"] == "mituan"
    assert inputs["paperbanana-version"]["default"] == "2.0.1"
    assert inputs["vlm-base-url"]["default"] == ""
    assert inputs["image-base-url"]["default"] == ""
    assert inputs["vlm-api-key"]["required"] is True
    assert inputs["image-api-key"]["required"] is True
    assert inputs["aspect-ratio"]["default"] == "3:2"
    assert inputs["resolution"]["default"] == "1K"


def test_action_connection_helper_keeps_keys_out_of_commands(monkeypatch):
    calls: list[tuple[list[str], dict[str, str]]] = []

    def record(command, *, check, env):
        assert check is True
        calls.append((command, env))

    monkeypatch.setattr(_CONNECTION_HELPER.subprocess, "run", record)
    env = {
        "PB_VLM_PROVIDER": "openai",
        "PB_VLM_BASE_URL": "https://vlm.example/v1",
        "PB_VLM_MODEL": "vlm-model",
        "PB_VLM_API_KEY": "vlm-secret",
        "PB_IMAGE_PROVIDER": "openai_imagen",
        "PB_IMAGE_BASE_URL": "https://image.example/v1",
        "PB_IMAGE_MODEL": "image-model",
        "PB_IMAGE_API_KEY": "image-secret",
        "PB_IMAGE_SIZE_MODE": "explicit_pixels",
    }

    _CONNECTION_HELPER.configure_connections(env)

    assert len(calls) == 2
    vlm_command, image_command = (call[0] for call in calls)
    assert vlm_command[-2:] == ["--base-url", "https://vlm.example/v1"]
    assert "--size-mode" not in vlm_command
    assert image_command[-4:] == [
        "--base-url",
        "https://image.example/v1",
        "--size-mode",
        "explicit_pixels",
    ]
    command_text = " ".join(vlm_command + image_command)
    assert "vlm-secret" not in command_text
    assert "image-secret" not in command_text
    assert "--api-key-env PB_VLM_API_KEY" in " ".join(vlm_command)
    assert "--api-key-env PB_IMAGE_API_KEY" in " ".join(image_command)


def test_action_connection_helper_accepts_internal_command_override(monkeypatch):
    calls: list[list[str]] = []

    def record(command, *, check, env):
        assert check is True
        calls.append(command)

    monkeypatch.setattr(_CONNECTION_HELPER.subprocess, "run", record)
    env = {
        "PAPERBANANA_CN_COMMAND": "/tmp/fake-paperbanana-cn",
        "PB_VLM_PROVIDER": "openai",
        "PB_VLM_MODEL": "vlm-model",
        "PB_VLM_API_KEY": "vlm-secret",
        "PB_IMAGE_PROVIDER": "openai_imagen",
        "PB_IMAGE_MODEL": "image-model",
        "PB_IMAGE_API_KEY": "image-secret",
        "PB_IMAGE_SIZE_MODE": "fixed",
    }

    _CONNECTION_HELPER.configure_connections(env)

    assert len(calls) == 2
    assert all(command[0] == "/tmp/fake-paperbanana-cn" for command in calls)
