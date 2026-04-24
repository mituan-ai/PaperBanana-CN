import types
from pathlib import Path
from unittest.mock import patch

from utils.config_loader import get_provider_image_api_key, load_provider_defaults
from utils.generation_utils import create_runtime_context
from utils.provider_connections import ProviderConnection, list_provider_connections
from utils.runtime_settings import resolve_runtime_settings


def test_env_vars_feed_builtin_gemini_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("PAPERBANANA_GEMINI_BASE_URL", "https://gemini.example")
    monkeypatch.setenv("PAPERBANANA_GEMINI_VLM_MODEL", "gemini-text")
    monkeypatch.setenv("PAPERBANANA_GEMINI_IMAGE_MODEL", "gemini-image")
    monkeypatch.setenv("PAPERBANANA_GEMINI_VLM_API_KEY", "gemini-vlm-key")
    monkeypatch.setenv("PAPERBANANA_GEMINI_IMAGE_API_KEY", "gemini-image-key")

    defaults = load_provider_defaults("gemini", {}, base_dir=tmp_path)

    assert defaults["base_url"] == "https://gemini.example"
    assert defaults["model_name"] == "gemini-text"
    assert defaults["image_model_name"] == "gemini-image"
    assert get_provider_image_api_key("gemini", {}, base_dir=tmp_path) == "gemini-image-key"


def test_custom_openai_connection_reads_paperbanana_env(monkeypatch, tmp_path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "provider_registry.yaml").write_text(
        "version: 1\nconnections:\n"
        "  - connection_id: custom-openai\n"
        "    display_name: Custom OpenAI\n"
        "    provider_type: openai_compatible\n"
        "    protocol_family: openai\n"
        "    supports_image: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PAPERBANANA_OPENAI_BASE_URL", "https://openai.example/v1")
    monkeypatch.setenv("PAPERBANANA_OPENAI_VLM_MODEL", "gpt-text")
    monkeypatch.setenv("PAPERBANANA_OPENAI_IMAGE_MODEL", "gpt-image")
    monkeypatch.setenv("PAPERBANANA_OPENAI_VLM_API_KEY", "openai-vlm-key")
    monkeypatch.setenv("PAPERBANANA_OPENAI_IMAGE_API_KEY", "openai-image-key")

    connection = next(item for item in list_provider_connections(base_dir=tmp_path) if item.connection_id == "custom-openai")
    settings = resolve_runtime_settings("custom-openai", base_dir=tmp_path)

    assert connection.base_url == "https://openai.example/v1"
    assert connection.text_model == "gpt-text"
    assert connection.image_model == "gpt-image"
    assert settings.api_key == "openai-vlm-key"
    assert settings.image_api_key == "openai-image-key"


def test_runtime_context_builds_separate_text_and_image_clients():
    calls = []

    def fake_create_openai_client(api_key, base_url="", extra_headers=None):
        client = types.SimpleNamespace(api_key=api_key, base_url=base_url, extra_headers=extra_headers)
        calls.append(client)
        return client

    with patch("utils.generation_utils._create_openai_client", side_effect=fake_create_openai_client):
        context = create_runtime_context(
            provider="openai_compatible",
            api_key="vlm-key",
            image_api_key="image-key",
            base_url="https://openai.example/v1",
        )

    assert context.openai_client.api_key == "vlm-key"
    assert context.openai_image_client.api_key == "image-key"
    assert calls[0].base_url == "https://openai.example/v1"
    assert calls[1].base_url == "https://openai.example/v1"
