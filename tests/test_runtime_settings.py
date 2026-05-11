import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.runtime_settings import (
    RuntimeSettings,
    build_provider_ui_defaults,
    build_runtime_context,
    resolve_runtime_settings,
)

BUILTIN_CONFIG_YAML = """gemini:
  base_url: https://gemini.example.com
  vlm_model: gemini-text
  image_model: gemini-image
  vlm_api_key: gemini-text-key
  image_api_key: gemini-image-key
openai:
  base_url: https://openai.example.com/v1
  vlm_model: gpt-text
  image_model: gpt-image
  vlm_api_key: openai-text-key
  image_api_key: openai-image-key
"""


CUSTOM_REGISTRY_YAML = """version: 1
connections:
  - connection_id: custom-text
    display_name: 自定义文本
    provider_type: openai_compatible
    protocol_family: openai
    base_url: https://text.example/v1
    api_key_env_var: CUSTOM_TEXT_API_KEY
    text_model: custom-text-model
    image_model: custom-text-image
    model_discovery_mode: hybrid
    model_allowlist:
      - custom-text-model
      - custom-text-image
    extra_headers:
      X-Text: 1
    supports_text: true
    supports_image: true
    enabled: true
  - connection_id: custom-image
    display_name: 自定义图像
    provider_type: openai_compatible
    protocol_family: openai
    base_url: https://image.example/v1
    api_key_env_var: CUSTOM_IMAGE_API_KEY
    text_model: custom-image-text
    image_model: custom-image-model
    model_discovery_mode: hybrid
    model_allowlist:
      - custom-image-text
      - custom-image-model
    extra_headers:
      X-Image: 1
    supports_text: true
    supports_image: true
    enabled: true
"""


class RuntimeSettingsTest(unittest.TestCase):
    ENV_KEYS = [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "GOOGLE_API_KEY",
        "CUSTOM_TEXT_API_KEY",
        "CUSTOM_IMAGE_API_KEY",
    ]

    def setUp(self):
        self._env_patcher = patch.dict(os.environ, {key: "" for key in self.ENV_KEYS})
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()

    def test_resolve_runtime_settings_uses_builtin_yaml_and_local_secret(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            local_dir = config_dir / "local"
            local_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(BUILTIN_CONFIG_YAML, encoding="utf-8")
            (local_dir / "openai_vlm_api_key.txt").write_text("local-openai-key\n", encoding="utf-8")

            settings = resolve_runtime_settings("openai", base_dir=root)

            self.assertEqual(settings.provider, "openai")
            self.assertEqual(settings.api_key, "local-openai-key")
            self.assertEqual(settings.image_api_key, "openai-image-key")
            self.assertEqual(settings.model_name, "gpt-text")
            self.assertEqual(settings.image_model_name, "gpt-image")
            self.assertEqual(settings.base_url, "https://openai.example.com/v1")
            self.assertEqual(settings.image_base_url, "https://openai.example.com/v1")

    def test_resolve_runtime_settings_keeps_dual_link_connections_separate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            local_dir = config_dir / "local"
            provider_dir = local_dir / "providers"
            provider_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(BUILTIN_CONFIG_YAML, encoding="utf-8")
            (config_dir / "provider_registry.yaml").write_text(CUSTOM_REGISTRY_YAML, encoding="utf-8")
            (provider_dir / "custom-text.txt").write_text("text-secret\n", encoding="utf-8")
            (provider_dir / "custom-image.txt").write_text("image-secret\n", encoding="utf-8")

            settings = resolve_runtime_settings(
                "openai",
                connection_id="custom-text",
                image_connection_id="custom-image",
                base_dir=root,
            )

            self.assertEqual(settings.provider, "openai_compatible")
            self.assertEqual(settings.image_provider, "openai_compatible")
            self.assertEqual(settings.connection_id, "custom-text")
            self.assertEqual(settings.image_connection_id, "custom-image")
            self.assertEqual(settings.api_key, "text-secret")
            self.assertEqual(settings.image_api_key, "image-secret")
            self.assertEqual(settings.base_url, "https://text.example/v1")
            self.assertEqual(settings.image_base_url, "https://image.example/v1")
            self.assertEqual(settings.model_name, "custom-text-model")
            self.assertEqual(settings.image_model_name, "custom-image-model")

    def test_build_provider_ui_defaults_exposes_builtin_display_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            local_dir = config_dir / "local"
            local_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(BUILTIN_CONFIG_YAML, encoding="utf-8")
            (local_dir / "openai_vlm_api_key.txt").write_text("local-openai-key\n", encoding="utf-8")

            defaults = build_provider_ui_defaults("openai", base_dir=root)

            self.assertEqual(defaults["api_key_default"], "local-openai-key")
            self.assertEqual(defaults["image_api_key_default"], "openai-image-key")
            self.assertEqual(defaults["model_name"], "gpt-text")
            self.assertEqual(defaults["image_model_name"], "gpt-image")
            self.assertEqual(defaults["base_url"], "https://openai.example.com/v1")
            self.assertEqual(defaults["vlm_base_url"], "https://openai.example.com/v1")
            self.assertEqual(defaults["image_base_url"], "https://openai.example.com/v1")

    def test_build_provider_ui_defaults_prefers_role_specific_yaml_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(
                "openai:\n"
                "  base_url: https://openai.example/v1\n"
                "  vlm_base_url: https://openai.vlm.example/v1\n"
                "  image_base_url: https://openai.image.example/v1\n"
                "  vlm_api_key: vlm-key\n"
                "  image_api_key: image-key\n"
                "  vlm_model: vlm-model\n"
                "  image_model: image-model\n",
                encoding="utf-8",
            )

            defaults = build_provider_ui_defaults("openai", base_dir=root)

            self.assertEqual(defaults["api_key_default"], "vlm-key")
            self.assertEqual(defaults["image_api_key_default"], "image-key")
            self.assertEqual(defaults["vlm_base_url"], "https://openai.vlm.example/v1")
            self.assertEqual(defaults["image_base_url"], "https://openai.image.example/v1")
            self.assertEqual(defaults["model_name"], "vlm-model")
            self.assertEqual(defaults["image_model_name"], "image-model")

    def test_build_runtime_context_delegates_to_generation_utils(self):
        settings = RuntimeSettings(
            provider="gemini",
            api_key="runtime-key",
            image_api_key="runtime-image-key",
            model_name="text-model",
            image_model_name="image-model",
            base_url="https://text.example/v1",
            image_base_url="https://image.example/v1",
            image_provider="openai",
            image_connection_id="custom-image",
            image_provider_display_name="自定义图像",
            image_extra_headers={"X-Image": "1"},
        )
        hook = lambda message: message

        with patch("utils.generation_utils.create_runtime_context", return_value={"ok": True}) as mocked_create:
            context = build_runtime_context(settings, status_hook=hook)

        self.assertEqual(context, {"ok": True})
        mocked_create.assert_called_once_with(
            connection_id="",
            provider="gemini",
            api_key="runtime-key",
            image_api_key="runtime-image-key",
            image_model_name="image-model",
            image_provider="openai",
            image_connection_id="custom-image",
            image_base_url="https://image.example/v1",
            image_extra_headers={"X-Image": "1"},
            base_url="https://text.example/v1",
            extra_headers={},
            event_hook=None,
            status_hook=hook,
            cancel_check=None,
        )


if __name__ == "__main__":
    unittest.main()
