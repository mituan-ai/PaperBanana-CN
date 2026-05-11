import tempfile
import unittest
from pathlib import Path

from utils.config_loader import (
    delete_provider_api_key,
    get_provider_api_key,
    load_model_config,
    load_provider_defaults,
    read_local_secret,
    write_provider_api_key,
)


class ConfigLoaderSecretWriteTest(unittest.TestCase):
    def test_write_provider_api_key_persists_google_key_to_official_local_txt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            written_path = write_provider_api_key(
                "gemini",
                "local-google-key",
                base_dir=root,
            )

            self.assertIsNotNone(written_path)
            self.assertEqual(written_path, root / "configs" / "local" / "gemini_vlm_api_key.txt")
            self.assertTrue(written_path.exists())
            self.assertEqual(
                read_local_secret("gemini", "vlm_api_key", base_dir=root),
                "local-google-key",
            )
            self.assertEqual(get_provider_api_key("gemini", {}, base_dir=root), "local-google-key")

    def test_write_provider_api_key_ignores_blank_updates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            local_dir = root / "configs" / "local"
            local_dir.mkdir(parents=True, exist_ok=True)
            secret_path = local_dir / "gemini_vlm_api_key.txt"
            secret_path.write_text("existing-key\n", encoding="utf-8")

            written_path = write_provider_api_key(
                "gemini",
                "   ",
                base_dir=root,
            )

            self.assertEqual(written_path, secret_path)
            self.assertEqual(secret_path.read_text(encoding="utf-8"), "existing-key\n")

    def test_delete_provider_api_key_removes_local_secret_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            local_dir = root / "configs" / "local"
            local_dir.mkdir(parents=True, exist_ok=True)
            secret_path = local_dir / "gemini_vlm_api_key.txt"
            secret_path.write_text("existing-key\n", encoding="utf-8")

            deleted_path = delete_provider_api_key("gemini", base_dir=root)

            self.assertEqual(deleted_path, secret_path)
            self.assertFalse(secret_path.exists())

    def test_load_provider_defaults_ignores_removed_provider_settings_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            local_dir = config_dir / "local"
            local_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(
                "openai:\n"
                "  base_url: https://model-config.example/v1\n"
                "  vlm_model: gpt-text\n"
                "  image_model: gpt-image\n"
                "  vlm_api_key: yaml-openai-key\n",
                encoding="utf-8",
            )
            (local_dir / "openai_vlm_api_key.txt").write_text("local-openai-key\n", encoding="utf-8")
            (local_dir / "provider_settings.yaml").write_text(
                "openai:\n"
                "  base_url: https://stale-provider-settings.example/v1\n"
                "  vlm_model: stale-text\n"
                "  image_model: stale-image\n",
                encoding="utf-8",
            )

            defaults = load_provider_defaults("openai", load_model_config(root), base_dir=root)

            self.assertEqual(defaults["base_url"], "https://model-config.example/v1")
            self.assertEqual(defaults["vlm_base_url"], "https://model-config.example/v1")
            self.assertEqual(defaults["image_base_url"], "https://model-config.example/v1")
            self.assertEqual(defaults["api_key"], "local-openai-key")
            self.assertEqual(defaults["vlm_api_key"], "local-openai-key")
            self.assertEqual(defaults["model_name"], "gpt-text")
            self.assertEqual(defaults["image_model_name"], "gpt-image")

    def test_load_provider_defaults_reads_role_specific_fields_when_present(self):
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

            defaults = load_provider_defaults("openai", load_model_config(root), base_dir=root)

            self.assertEqual(defaults["vlm_base_url"], "https://openai.vlm.example/v1")
            self.assertEqual(defaults["image_base_url"], "https://openai.image.example/v1")
            self.assertEqual(defaults["vlm_api_key"], "vlm-key")
            self.assertEqual(defaults["image_api_key"], "image-key")
            self.assertEqual(defaults["model_name"], "vlm-model")
            self.assertEqual(defaults["image_model_name"], "image-model")


if __name__ == "__main__":
    unittest.main()
