import tempfile
import unittest
from pathlib import Path

from utils.config_loader import (
    delete_provider_api_key,
    read_local_secret,
    write_provider_api_key,
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
                read_local_secret("api_keys", "google_api_key", base_dir=root),
                "local-google-key",
            )

    def test_write_provider_api_key_ignores_blank_updates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            local_dir = root / "configs" / "local"
            local_dir.mkdir(parents=True, exist_ok=True)
            secret_path = local_dir / "google_api_key.txt"
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
            secret_path = local_dir / "google_api_key.txt"
            secret_path.write_text("existing-key\n", encoding="utf-8")

            deleted_path = delete_provider_api_key("gemini", base_dir=root)

            self.assertEqual(deleted_path, secret_path)
            self.assertFalse(secret_path.exists())


if __name__ == "__main__":
    unittest.main()
