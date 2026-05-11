from utils.config_loader import load_model_config, load_provider_defaults
from utils.runtime_settings import resolve_runtime_settings


def test_official_environment_variables_override_yaml_and_local_secret(monkeypatch, tmp_path):
    config_dir = tmp_path / "configs"
    local_dir = config_dir / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "model_config.yaml").write_text(
        "openai:\n"
        "  base_url: https://yaml.example/v1\n"
        "  vlm_model: yaml-text\n"
        "  image_model: yaml-image\n"
        "  vlm_api_key: yaml-openai-key\n"
        "  image_api_key: yaml-openai-image-key\n"
        "gemini:\n"
        "  base_url: https://yaml-gemini.example\n"
        "  vlm_model: yaml-gemini-text\n"
        "  image_model: yaml-gemini-image\n"
        "  vlm_api_key: yaml-gemini-key\n"
        "  image_api_key: yaml-gemini-image-key\n",
        encoding="utf-8",
    )
    (local_dir / "openai_vlm_api_key.txt").write_text("local-openai-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("GOOGLE_API_KEY", "env-google-key")

    openai_defaults = load_provider_defaults("openai", load_model_config(tmp_path), base_dir=tmp_path)
    gemini_defaults = load_provider_defaults("gemini", load_model_config(tmp_path), base_dir=tmp_path)

    assert openai_defaults["api_key"] == "env-openai-key"
    assert openai_defaults["base_url"] == "https://env.example/v1"
    assert openai_defaults["model_name"] == "yaml-text"
    assert openai_defaults["image_model_name"] == "yaml-image"
    assert gemini_defaults["api_key"] == "env-google-key"
    assert gemini_defaults["base_url"] == "https://yaml-gemini.example"


def test_removed_provider_settings_yaml_is_ignored(monkeypatch, tmp_path):
    config_dir = tmp_path / "configs"
    local_dir = config_dir / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "model_config.yaml").write_text(
        "openai:\n"
        "  base_url: https://yaml.example/v1\n"
        "  vlm_model: yaml-text\n"
        "  image_model: yaml-image\n"
        "  vlm_api_key: yaml-openai-key\n",
        encoding="utf-8",
    )
    (local_dir / "provider_settings.yaml").write_text(
        "openai:\n"
        "  base_url: https://stale.example/v1\n"
        "  vlm_model: stale-text\n"
        "  image_model: stale-image\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

    defaults = load_provider_defaults("openai", load_model_config(tmp_path), base_dir=tmp_path)

    assert defaults["base_url"] == "https://yaml.example/v1"
    assert defaults["model_name"] == "yaml-text"
    assert defaults["image_model_name"] == "yaml-image"


def test_custom_connection_uses_its_own_registry_and_not_generic_openai_env(monkeypatch, tmp_path):
    config_dir = tmp_path / "configs"
    local_dir = config_dir / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "model_config.yaml").write_text(
        "gemini:\n"
        "  base_url: https://gemini.example\n"
        "  vlm_model: default-text\n"
        "  image_model: default-image\n"
        "  vlm_api_key: gemini-key\n",
        encoding="utf-8",
    )
    (config_dir / "provider_registry.yaml").write_text(
        "version: 1\nconnections:\n"
        "  - connection_id: custom-openai\n"
        "    display_name: Custom OpenAI\n"
        "    provider_type: openai_compatible\n"
        "    protocol_family: openai\n"
        "    base_url: https://example.com/v1\n"
        "    api_key_env_var: CUSTOM_OPENAI_API_KEY\n"
        "    text_model: custom-text\n"
        "    image_model: custom-image\n"
        "    model_discovery_mode: hybrid\n"
        "    model_allowlist:\n"
        "      - custom-text\n"
        "      - custom-image\n"
        "    extra_headers:\n"
        "      X-Test: abc\n"
        "    supports_text: true\n"
        "    supports_image: true\n"
        "    enabled: true\n",
        encoding="utf-8",
    )
    (local_dir / "providers").mkdir(parents=True, exist_ok=True)
    (local_dir / "providers" / "custom-openai.txt").write_text("custom-local-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example/v1")
    settings = resolve_runtime_settings("gemini", connection_id="custom-openai", base_dir=tmp_path)

    assert settings.provider == "openai_compatible"
    assert settings.connection_id == "custom-openai"
    assert settings.api_key == "custom-local-key"
    assert settings.base_url == "https://example.com/v1"
    assert settings.model_name == "custom-text"
    assert settings.image_model_name == "custom-image"
    assert settings.extra_headers == {"X-Test": "abc"}
