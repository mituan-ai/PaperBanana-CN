import json
import tempfile
import unittest
from pathlib import Path

from utils.result_bundle import (
    RESULT_BUNDLE_SCHEMA,
    RESULT_BUNDLE_VERSION,
    build_run_manifest,
    companion_bundle_path,
    load_result_bundle,
    write_result_bundle,
)


class ResultBundleTest(unittest.TestCase):
    def test_load_legacy_json_array_infers_manifest_and_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "legacy.json"
            payload = [
                {
                    "candidate_id": 0,
                    "dataset_name": "CustomBench",
                    "task_name": "plot",
                    "exp_mode": "dev_planner",
                    "provider": "gemini",
                    "eval_image_field": "target_plot_desc0_base64_jpg",
                    "target_plot_desc0_base64_jpg": "abc",
                },
                {
                    "candidate_id": 1,
                    "dataset_name": "CustomBench",
                    "task_name": "plot",
                    "status": "failed",
                    "error": "boom",
                },
            ]
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            bundle = load_result_bundle(path)

            self.assertEqual(bundle["manifest"]["dataset_name"], "CustomBench")
            self.assertEqual(bundle["manifest"]["task_name"], "plot")
            self.assertEqual(bundle["manifest"]["provider"], "gemini")
            self.assertEqual(bundle["manifest"]["source_file"], "legacy.json")
            self.assertEqual(bundle["summary"]["total_candidates"], 2)
            self.assertEqual(bundle["summary"]["failed_candidate_ids"], [1])
            self.assertEqual(bundle["schema"], RESULT_BUNDLE_SCHEMA)
            self.assertEqual(bundle["schema_version"], RESULT_BUNDLE_VERSION)

    def test_load_jsonl_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.jsonl"
            lines = [
                json.dumps(
                    {
                        "candidate_id": 0,
                        "dataset_name": "LineBench",
                        "task_name": "diagram",
                        "exp_mode": "demo_planner_critic",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "candidate_id": 1,
                        "dataset_name": "LineBench",
                        "task_name": "diagram",
                    },
                    ensure_ascii=False,
                ),
            ]
            path.write_text("\n".join(lines), encoding="utf-8")

            bundle = load_result_bundle(path)

            self.assertEqual(len(bundle["results"]), 2)
            self.assertEqual(bundle["manifest"]["dataset_name"], "LineBench")
            self.assertEqual(bundle["manifest"]["task_name"], "diagram")
            self.assertEqual(bundle["manifest"]["source_file"], "results.jsonl")

    def test_load_wrapped_smoke_payload_without_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "smoke.json"
            payload = {
                "provider": "gemini",
                "dataset_name": "SmokeBench",
                "task_name": "diagram",
                "model_name": "gemini-text",
                "image_model_name": "gemini-image",
                "exp_mode": "demo_planner_critic",
                "summary": {"total_candidates": 1},
                "failures": [],
                "results": [
                    {
                        "candidate_id": 0,
                        "dataset_name": "SmokeBench",
                        "task_name": "diagram",
                        "eval_image_field": "target_diagram_desc0_base64_jpg",
                        "target_diagram_desc0_base64_jpg": "abc",
                    }
                ],
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            bundle = load_result_bundle(path)

            self.assertEqual(bundle["manifest"]["producer"], "legacy_file")
            self.assertEqual(bundle["manifest"]["provider"], "gemini")
            self.assertEqual(bundle["manifest"]["model_name"], "gemini-text")
            self.assertEqual(bundle["manifest"]["image_model_name"], "gemini-image")
            self.assertEqual(bundle["summary"], {"total_candidates": 1})
            self.assertEqual(bundle["failures"], [])

    def test_write_result_bundle_creates_standard_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "run.bundle.json"
            results = [
                {
                    "candidate_id": 0,
                    "dataset_name": "BundleBench",
                    "task_name": "diagram",
                    "eval_image_field": "target_diagram_desc0_base64_jpg",
                    "target_diagram_desc0_base64_jpg": "abc",
                }
            ]
            manifest = build_run_manifest(
                producer="demo",
                result_count=len(results),
                dataset_name="BundleBench",
                task_name="diagram",
                exp_mode="demo_planner_critic",
                split_name="demo",
                provider="gemini",
            )

            write_result_bundle(path, results, manifest=manifest)
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["schema"], RESULT_BUNDLE_SCHEMA)
            self.assertEqual(payload["schema_version"], RESULT_BUNDLE_VERSION)
            self.assertEqual(payload["manifest"]["producer"], "demo")
            self.assertEqual(payload["manifest"]["dataset_name"], "BundleBench")
            self.assertEqual(payload["manifest"]["result_count"], 1)
            self.assertEqual(companion_bundle_path(Path(temp_dir) / "run.json").name, "run.bundle.json")


if __name__ == "__main__":
    unittest.main()
