import asyncio
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class _FakeProcessor:
    def __init__(self, *args, **kwargs):
        return None

    async def process_queries_batch(self, *args, **kwargs):
        if False:
            yield None
        return

    def shutdown(self):
        return None


class MainProviderConnectionsTest(unittest.TestCase):
    def _run_main_with_args(self, argv: list[str], *, provider: str, connection_id: str) -> list[dict]:
        captured_exp_config_kwargs: list[dict] = []
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        work_dir = Path(temp_dir.name)
        dataset_file = work_dir / "input.json"
        dataset_file.write_text(json.dumps([], ensure_ascii=False), encoding="utf-8")
        result_dir = work_dir / "results"
        result_dir.mkdir(parents=True, exist_ok=True)

        def fake_exp_config(**kwargs):
            captured_exp_config_kwargs.append(dict(kwargs))
            return types.SimpleNamespace(
                dataset_name=kwargs["dataset_name"],
                task_name=kwargs["task_name"],
                split_name=kwargs["split_name"],
                exp_mode=kwargs["exp_mode"],
                retrieval_setting=kwargs["retrieval_setting"],
                curated_profile=kwargs["curated_profile"],
                max_critic_rounds=kwargs["max_critic_rounds"],
                concurrency_mode=kwargs["concurrency_mode"],
                max_concurrent=kwargs["max_concurrent"],
                model_name=kwargs["model_name"] or "text-model",
                image_model_name=kwargs["image_model_name"] or "image-model",
                provider=provider,
                connection_id=connection_id,
                result_dir=result_dir,
                exp_name="demo_run",
                runtime_settings=types.SimpleNamespace(),
            )

        async def fake_write_json_payload_async(path, payload):
            Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return Path(path)

        async def fake_write_result_bundle_async(path, results, manifest, summary=None, failures=None):
            Path(path).write_text(
                json.dumps({"manifest": manifest, "results": results}, ensure_ascii=False),
                encoding="utf-8",
            )
            return Path(path)

        with patch("sys.argv", argv), \
            patch.object(main.config, "ExpConfig", side_effect=fake_exp_config), \
            patch.object(main, "get_dataset_split_path", return_value=dataset_file), \
            patch.object(main, "load_resumed_results", return_value=[]), \
            patch.object(main, "prepare_pending_inputs", return_value=[]), \
            patch.object(main.paperviz_processor, "PaperVizProcessor", side_effect=_FakeProcessor), \
            patch.object(main, "write_json_payload_async", side_effect=fake_write_json_payload_async), \
            patch.object(main, "write_result_bundle_async", side_effect=fake_write_result_bundle_async), \
            patch.object(main, "write_cli_checkpoint", return_value=None), \
            patch.object(main, "append_cli_checkpoint_event", return_value=None), \
            patch.object(main, "checkpoint_path_for_output", side_effect=lambda output: Path(str(output) + ".checkpoint.json")), \
            patch.object(main, "checkpoint_event_log_path", side_effect=lambda checkpoint: Path(str(checkpoint) + ".events.jsonl")):
            asyncio.run(main.main())

        return captured_exp_config_kwargs

    def test_connection_id_argument_is_forwarded_alongside_legacy_provider(self):
        captured = self._run_main_with_args(
            [
                "main.py",
                "--dataset_name", "PaperBananaBench",
                "--task_name", "diagram",
                "--split_name", "test",
                "--exp_mode", "dev_full",
                "--provider", "gemini",
                "--connection_id", "custom-openai",
            ],
            provider="openai_compatible",
            connection_id="custom-openai",
        )

        self.assertEqual(captured[0]["provider"], "gemini")
        self.assertEqual(captured[0]["connection_id"], "custom-openai")

    def test_legacy_provider_argument_still_works_without_connection_id(self):
        captured = self._run_main_with_args(
            [
                "main.py",
                "--dataset_name", "PaperBananaBench",
                "--task_name", "diagram",
                "--split_name", "test",
                "--exp_mode", "dev_full",
                "--provider", "openrouter",
            ],
            provider="openrouter",
            connection_id="",
        )

        self.assertEqual(captured[0]["provider"], "openrouter")
        self.assertEqual(captured[0]["connection_id"], "")


if __name__ == "__main__":
    unittest.main()
