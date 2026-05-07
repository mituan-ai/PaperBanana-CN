import types
from unittest.mock import patch

from utils.config_loader import (
    get_provider_image_api_key,
    load_provider_defaults,
    write_provider_runtime_defaults,
)
from utils.generation_utils import create_runtime_context
from utils.provider_connections import ProviderConnection, list_provider_connections
from utils.runtime_settings import resolve_runtime_settings


def test_project_local_config_ignores_provider_environment_by_default(monkeypatch, tmp_path):
    config_dir = tmp_path / "configs"
    local_dir = config_dir / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "model_config.yaml").write_text(
        "gemini:\n"
        "  base_url: https://gemini.local\n"
        "  vlm_model: gemini-local-text\n"
        "  image_model: gemini-local-image\n",
        encoding="utf-8",
    )
    (local_dir / "provider_settings.yaml").write_text(
        "gemini:\n"
        "  base_url: https://gemini.saved\n"
        "  vlm_model: gemini-saved-text\n"
        "  image_model: gemini-saved-image\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PAPERBANANA_GEMINI_BASE_URL", "https://gemini.example")
    monkeypatch.setenv("PAPERBANANA_GEMINI_VLM_MODEL", "gemini-text")
    monkeypatch.setenv("PAPERBANANA_GEMINI_IMAGE_MODEL", "gemini-image")
    monkeypatch.setenv("PAPERBANANA_GEMINI_VLM_API_KEY", "gemini-vlm-key")
    monkeypatch.setenv("PAPERBANANA_GEMINI_IMAGE_API_KEY", "gemini-image-key")

    defaults = load_provider_defaults("gemini", {}, base_dir=tmp_path)

    assert defaults["base_url"] == "https://gemini.saved"
    assert defaults["model_name"] == "gemini-saved-text"
    assert defaults["image_model_name"] == "gemini-saved-image"
    assert get_provider_image_api_key("gemini", {}, base_dir=tmp_path) == ""


def test_provider_environment_is_only_used_when_explicitly_requested(monkeypatch, tmp_path):
    monkeypatch.setenv("PAPERBANANA_OPENAI_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("PAPERBANANA_OPENAI_VLM_MODEL", "env-text")
    monkeypatch.setenv("PAPERBANANA_OPENAI_IMAGE_MODEL", "env-image")
    monkeypatch.setenv("PAPERBANANA_OPENAI_VLM_API_KEY", "env-vlm-key")

    defaults_without_env = load_provider_defaults("openai", {}, base_dir=tmp_path)
    defaults_with_env = load_provider_defaults("openai", {}, base_dir=tmp_path, use_env=True)

    assert defaults_without_env["base_url"] == "https://api.openai.com/v1"
    assert defaults_without_env["model_name"] == "gpt-5.4-mini"
    assert defaults_without_env["api_key"] == ""
    assert defaults_with_env["base_url"] == "https://env.example/v1"
    assert defaults_with_env["model_name"] == "env-text"
    assert defaults_with_env["image_model_name"] == "env-image"
    assert defaults_with_env["api_key"] == "env-vlm-key"


def test_role_specific_provider_urls_do_not_clobber_each_other(tmp_path):
    write_provider_runtime_defaults(
        "openai",
        base_url="https://text.example/v1",
        base_url_role="vlm",
        model_name="gpt-text",
        base_dir=tmp_path,
    )
    write_provider_runtime_defaults(
        "openai",
        base_url="https://image.example/v1",
        base_url_role="image",
        image_model_name="gpt-image-2",
        base_dir=tmp_path,
    )

    defaults = load_provider_defaults("openai", {}, base_dir=tmp_path)

    assert defaults["base_url"] == "https://api.openai.com/v1"
    assert defaults["vlm_base_url"] == "https://text.example/v1"
    assert defaults["image_base_url"] == "https://image.example/v1"
    assert defaults["model_name"] == "gpt-text"
    assert defaults["image_model_name"] == "gpt-image-2"


def test_custom_openai_connection_ignores_generic_openai_env(monkeypatch, tmp_path):
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

    assert connection.base_url == ""
    assert connection.text_model == ""
    assert connection.image_model == ""
    assert settings.api_key == ""
    assert settings.image_api_key == ""


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
