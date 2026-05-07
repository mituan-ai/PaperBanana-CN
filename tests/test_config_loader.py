import tempfile
import unittest
from pathlib import Path

from utils.config_loader import (
    delete_provider_api_key,
    get_local_provider_settings_path,
    get_provider_api_key,
    read_local_secret,
    read_local_provider_settings,
    update_local_provider_settings,
    write_provider_api_key,
    write_provider_runtime_defaults,
)


class ConfigLoaderSecretWriteTest(unittest.TestCase):
    def test_write_provider_api_key_persists_google_key_to_local_txt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            written_path = write_provider_api_key(
                "gemini",
                "local-google-key",
                base_dir=root,
            )

            self.assertIsNotNone(written_path)
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

    def test_update_local_provider_settings_skips_identical_disk_write(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            settings_path = get_local_provider_settings_path(root)

            first_path = update_local_provider_settings(
                "openai",
                {"vlm_base_url": "https://api.example/v1", "vlm_model": "gpt-text"},
                base_dir=root,
            )
            first_text = settings_path.read_text(encoding="utf-8")

            second_path = update_local_provider_settings(
                "openai",
                {"vlm_base_url": "https://api.example/v1", "vlm_model": "gpt-text"},
                base_dir=root,
            )

            self.assertEqual(first_path, second_path)
            self.assertEqual(settings_path.read_text(encoding="utf-8"), first_text)
            self.assertEqual(
                read_local_provider_settings(root)["openai"]["vlm_base_url"],
                "https://api.example/v1",
            )

    def test_write_provider_runtime_defaults_supports_empty_noop(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            settings_path = get_local_provider_settings_path(root)

            written_path = write_provider_runtime_defaults("openai", base_dir=root)

            self.assertEqual(written_path, settings_path)
            self.assertFalse(settings_path.exists())


if __name__ == "__main__":
    unittest.main()
