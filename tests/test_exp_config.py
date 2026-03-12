import tempfile
import unittest
from pathlib import Path

from utils.config import ExpConfig, build_run_name


CONFIG_YAML = """defaults:
  model_name: gemini-default-text
  image_model_name: gemini-default-image
evolink:
  api_key: ""
  base_url: https://api.evolink.ai
  model_name: evolink-text
  image_model_name: evolink-image
"""


class ExpConfigProviderDefaultsTest(unittest.TestCase):
    def test_exp_config_defaults_to_gemini_provider(self):
        exp_config = ExpConfig(dataset_name="PaperBananaBench")

        self.assertEqual(exp_config.provider, "gemini")

    def test_gemini_provider_uses_default_section(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            config_dir = work_dir / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")

            exp_config = ExpConfig(
                dataset_name="PaperBananaBench",
                task_name="diagram",
                provider="gemini",
                work_dir=work_dir,
            )

            self.assertEqual(exp_config.model_name, "gemini-default-text")
            self.assertEqual(exp_config.image_model_name, "gemini-default-image")

    def test_evolink_provider_uses_evolink_section(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            config_dir = work_dir / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")

            exp_config = ExpConfig(
                dataset_name="PaperBananaBench",
                task_name="plot",
                provider="evolink",
                work_dir=work_dir,
            )

            self.assertEqual(exp_config.model_name, "evolink-text")
            self.assertEqual(exp_config.image_model_name, "evolink-image")
            self.assertTrue(exp_config.result_dir.exists())

    def test_exp_name_includes_provider_and_seconds_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            config_dir = work_dir / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")

            exp_config = ExpConfig(
                dataset_name="PaperBananaBench",
                task_name="diagram",
                provider="gemini",
                model_name="gemini-3.1-flash-image-preview",
                retrieval_setting="auto",
                exp_mode="demo_full",
                split_name="test",
                timestamp="0310_123456",
                work_dir=work_dir,
            )

            self.assertTrue(exp_config.exp_name.startswith("0310_123456_gemini_"))
            self.assertIn("auto", exp_config.exp_name)
            self.assertIn("demo-full", exp_config.exp_name)

    def test_build_run_name_sanitizes_model_identifiers(self):
        run_name = build_run_name(
            timestamp="20260310_101530_123456",
            provider="gemini",
            model_name="gemini-3.1-flash-lite-preview",
            image_model_name="gemini/3.1 pro image preview",
            retrieval_setting="auto-full",
            exp_mode="demo_full",
            split_name="demo",
        )

        self.assertIn("gemini", run_name)
        self.assertIn("gemini-3-1-pro-image-pre", run_name)
        self.assertNotIn("/", run_name)
        self.assertNotIn(" ", run_name)

    def test_manual_alias_normalizes_to_curated_profile(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            config_dir = work_dir / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "model_config.yaml").write_text(CONFIG_YAML, encoding="utf-8")

            exp_config = ExpConfig(
                dataset_name="PaperBananaBench",
                task_name="diagram",
                provider="gemini",
                retrieval_setting="manual",
                curated_profile=" paper profile ",
                exp_mode="demo_full",
                split_name="demo",
                timestamp="0310_123456",
                work_dir=work_dir,
            )

            self.assertEqual(exp_config.retrieval_setting, "curated")
            self.assertEqual(exp_config.curated_profile, "paper-profile")
            self.assertIn("curated-paper-profil", exp_config.exp_name)


if __name__ == "__main__":
    unittest.main()
