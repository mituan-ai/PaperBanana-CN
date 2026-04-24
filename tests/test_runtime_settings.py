import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from utils.runtime_settings import (
    RuntimeSettings,
    build_runtime_context,
    build_provider_ui_defaults,
    resolve_runtime_settings,
)


CONFIG_YAML = """defaults:
  model_name: gemini-default-text
  image_model_name: gemini-default-image
gemini:
  base_url: https://gemini.example.com
  vlm_model: gemini-text
  image_model: gemini-image
  vlm_api_key: yaml-gemini-text-key
  image_api_key: yaml-gemini-image-key
openai:
  base_url: https://openai.example.com/v1
  vlm_model: gpt-text
  image_model: gpt-image
  vlm_api_key: yaml-openai-text-key
  image_api_key: yaml-openai-image-key
evolink:
  api_key: yaml-evolink-key
  base_url: https://api.evolink.ai
  model_name: evolink-text
  image_model_name: evolink-image
"""

PROVIDER_REGISTRY_YAML = """version: 1
connections:
  - connection_id: custom-openai
    display_name: 自定义 OpenAI
    provider_type: openai_compatible
    protocol_family: openai
    base_url: https://example.com/v1
    api_key_env_var: CUSTOM_OPENAI_API_KEY
    text_model: custom-text
    image_model: custom-image
    model_discovery_mode: hybrid
    model_allowlist:
      - custom-text
      - custom-image
    extra_headers:
      X-Test: abc
    supports_text: true
    supports_image: true
    enabled: true
"""


class RuntimeSettingsTest(unittest.TestCase):
    ENV_KEYS = [
        "PAPERBANANA_GEMINI_VLM_API_KEY",
        "PAPERBANANA_GEMINI_IMAGE_API_KEY",
        "PAPERBANANA_GEMINI_VLM_MODEL",
        "PAPERBANANA_GEMINI_IMAGE_MODEL",
        "PAPERBANANA_GEMINI_BASE_URL",
        "PAPERBANANA_OPENAI_VLM_API_KEY",
        "PAPERBANANA_OPENAI_IMAGE_API_KEY",
        "PAPERBANANA_OPENAI_BASE_URL",
        "PAPERBANANA_OPENAI_VLM_MODEL",
        "PAPERBANANA_OPENAI_IMAGE_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_VLM_API_KEY",
        "OPENAI_IMAGE_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_VLM_MODEL",
        "OPENAI_IMAGE_MODEL",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_IMAGE_API_KEY",
        "GEMINI_IMAGE_API_KEY",
        "GOOGLE_BASE_URL",
        "GEMINI_BASE_URL",
        "EVOLINK_API_KEY",
        "OPENROUTER_API_KEY",
    ]

    def setUp(self):
        self._env_patcher = patch.dict(os.environ, {key: "" for key in self.ENV_KEYS})
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()

    def _write_custom_connection_fixture(self, root: Path) -> None:
        config_dir = root / "configs"
        local_dir = config_dir / "local"
        provider_dir = local_dir / "providers"
        provider_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
        (config_dir / "provider_registry.yaml").write_text(PROVIDER_REGISTRY_YAML, encoding="utf-8")
        (provider_dir / "custom-openai.txt").write_text("custom-local-key\n", encoding="utf-8")

    def test_resolve_runtime_settings_uses_local_secret_then_yaml_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            local_dir = config_dir / "local"
            local_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
            (local_dir / "google_api_key.txt").write_text("local-google-key", encoding="utf-8")

            settings = resolve_runtime_settings(
                "gemini",
                base_dir=root,
            )

            self.assertEqual(settings.provider, "gemini")
            self.assertEqual(settings.api_key, "yaml-gemini-text-key")
            self.assertEqual(settings.image_api_key, "yaml-gemini-image-key")
            self.assertEqual(settings.model_name, "gemini-text")
            self.assertEqual(settings.image_model_name, "gemini-image")

    def test_resolve_runtime_settings_prefers_connection_id_for_custom_connection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_custom_connection_fixture(root)

            settings = resolve_runtime_settings(
                "gemini",
                connection_id="custom-openai",
                base_dir=root,
            )

            self.assertEqual(settings.provider, "openai_compatible")
            self.assertEqual(settings.connection_id, "custom-openai")
            self.assertEqual(settings.provider_display_name, "自定义 OpenAI")
            self.assertEqual(settings.api_key, "custom-local-key")
            self.assertEqual(settings.base_url, "https://example.com/v1")
            self.assertEqual(settings.model_name, "custom-text")
            self.assertEqual(settings.image_model_name, "custom-image")
            self.assertEqual(settings.extra_headers, {"X-Test": "abc"})

    def test_build_provider_ui_defaults_reads_custom_connection_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_custom_connection_fixture(root)

            defaults = build_provider_ui_defaults("custom-openai", base_dir=root)

            self.assertEqual(defaults["connection_id"], "custom-openai")
            self.assertEqual(defaults["display_name"], "自定义 OpenAI")
            self.assertEqual(defaults["provider_type"], "openai_compatible")
            self.assertEqual(defaults["base_url"], "https://example.com/v1")
            self.assertEqual(defaults["extra_headers"], {"X-Test": "abc"})
            self.assertTrue(defaults["supports_image"])

    def test_build_provider_ui_defaults_exposes_provider_specific_labels(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")

            defaults = build_provider_ui_defaults("evolink", base_dir=root)

            self.assertEqual(defaults["api_key_label"], "API Key")
            self.assertEqual(defaults["model_name"], "evolink-text")
            self.assertEqual(defaults["image_model_name"], "evolink-image")
            self.assertEqual(defaults["api_key_default"], "yaml-evolink-key")
            self.assertEqual(defaults["base_url"], "https://api.evolink.ai")

    def test_resolve_runtime_settings_supports_builtin_openai(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")

            settings = resolve_runtime_settings("openai", base_dir=root)

            self.assertEqual(settings.provider, "openai")
            self.assertEqual(settings.connection_id, "openai")
            self.assertEqual(settings.api_key, "yaml-openai-text-key")
            self.assertEqual(settings.image_api_key, "yaml-openai-image-key")
            self.assertEqual(settings.model_name, "gpt-text")
            self.assertEqual(settings.image_model_name, "gpt-image")
            self.assertEqual(settings.base_url, "https://openai.example.com/v1")

            defaults = build_provider_ui_defaults("openai", base_dir=root)
            self.assertEqual(defaults["api_key_default"], "yaml-openai-text-key")
            self.assertEqual(defaults["image_api_key_default"], "yaml-openai-image-key")

    def test_resolve_runtime_settings_keeps_text_and_image_connections_independent(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")

            settings = resolve_runtime_settings(
                "openai",
                model_name="gpt-text",
                image_connection_id="gemini",
                image_model_name="gemini-image",
                base_dir=root,
            )

            self.assertEqual(settings.provider, "openai")
            self.assertEqual(settings.api_key, "yaml-openai-text-key")
            self.assertEqual(settings.model_name, "gpt-text")
            self.assertEqual(settings.base_url, "https://openai.example.com/v1")
            self.assertEqual(settings.image_provider, "gemini")
            self.assertEqual(settings.image_api_key, "yaml-gemini-image-key")
            self.assertEqual(settings.image_model_name, "gemini-image")
            self.assertEqual(settings.image_base_url, "https://gemini.example.com")

    def test_build_runtime_context_delegates_to_generation_utils(self):
        settings = RuntimeSettings(
            provider="gemini",
            api_key="runtime-key",
            model_name="text-model",
            image_model_name="image-model",
            base_url="",
        )
        hook = lambda message: message

        with patch("utils.generation_utils.create_runtime_context", return_value={"ok": True}) as mocked_create:
            context = build_runtime_context(settings, status_hook=hook)

        self.assertEqual(context, {"ok": True})
        mocked_create.assert_called_once_with(
            connection_id="",
            provider="gemini",
            api_key="runtime-key",
            image_api_key="",
            image_provider="gemini",
            image_connection_id="",
            image_base_url="",
            image_extra_headers={},
            base_url="",
            extra_headers={},
            event_hook=None,
            status_hook=hook,
            cancel_check=None,
        )


if __name__ == "__main__":
    unittest.main()
