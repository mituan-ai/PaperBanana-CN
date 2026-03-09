import asyncio
import base64
import importlib
import json
import sys
import tempfile
import time
import types
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

from utils.result_bundle import build_run_manifest, write_result_bundle


if "streamlit" not in sys.modules:
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.set_page_config = lambda *args, **kwargs: None
    fake_streamlit.session_state = {}
    sys.modules["streamlit"] = fake_streamlit

demo = importlib.import_module("demo")


def _build_png_base64() -> str:
    image = Image.new("RGB", (8, 8), color=(12, 34, 56))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class GenerationBackgroundJobTest(unittest.TestCase):
    def setUp(self):
        demo.st.session_state.clear()

    def _wait_for_terminal_snapshot(self, job_id: str, timeout: float = 5.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            snapshot = demo.get_generation_job_snapshot(job_id)
            if snapshot and snapshot.get("status") in {"completed", "cancelled", "failed"}:
                return snapshot
            time.sleep(0.05)
        self.fail(f"generation job {job_id} did not finish within {timeout}s")

    def test_background_generation_job_records_results_and_artifacts(self):
        original_process = demo.process_parallel_candidates
        original_save = demo.save_demo_generation_artifacts

        async def fake_process_parallel_candidates(data_list, progress_callback=None, status_callback=None, **kwargs):
            if progress_callback:
                progress_callback(0, 2, 1)
            if status_callback:
                status_callback("候选 0: 开始处理")
            await asyncio.sleep(0.01)
            results = [
                {
                    "candidate_id": 0,
                    "task_name": "diagram",
                    "dataset_name": "PaperBananaBench",
                    "exp_mode": "demo_planner_critic",
                    "eval_image_field": "target_diagram_desc0_base64_jpg",
                    "target_diagram_desc0_base64_jpg": _build_png_base64(),
                },
                {
                    "candidate_id": 1,
                    "task_name": "diagram",
                    "dataset_name": "PaperBananaBench",
                    "exp_mode": "demo_planner_critic",
                    "eval_image_field": "target_diagram_desc0_base64_jpg",
                    "target_diagram_desc0_base64_jpg": _build_png_base64(),
                },
            ]
            if progress_callback:
                progress_callback(2, 2, 1)
            return results, 1

        def fake_save_demo_generation_artifacts(**kwargs):
            return {
                "summary": {"total_candidates": 2},
                "failures": [],
                "json_file": "D:/tmp/demo_generation.json",
                "bundle_file": "D:/tmp/demo_generation.bundle.json",
                "manifest": {},
            }

        demo.process_parallel_candidates = fake_process_parallel_candidates
        demo.save_demo_generation_artifacts = fake_save_demo_generation_artifacts
        job_id = None
        try:
            job_id = demo.start_generation_background_job(
                dataset_name="PaperBananaBench",
                task_name="diagram",
                exp_mode="demo_planner_critic",
                retrieval_setting="none",
                curated_profile="default",
                provider="gemini",
                api_key="local-test-key",
                model_name="gemini-3.1-flash-lite-preview",
                image_model_name="gemini-3.1-flash-image-preview",
                concurrency_mode="manual",
                max_concurrent=1,
                num_candidates=2,
                max_critic_rounds=1,
                aspect_ratio="16:9",
                image_resolution="2K",
                content="paper method",
                visual_intent="draw a pipeline",
            )
            snapshot = self._wait_for_terminal_snapshot(job_id)

            self.assertEqual(snapshot["status"], "completed")
            self.assertEqual(len(snapshot["results"]), 2)
            self.assertEqual(snapshot["json_file"], "D:/tmp/demo_generation.json")
            self.assertEqual(snapshot["bundle_file"], "D:/tmp/demo_generation.bundle.json")
            self.assertEqual(snapshot["curated_profile"], "default")
        finally:
            demo.process_parallel_candidates = original_process
            demo.save_demo_generation_artifacts = original_save
            if job_id:
                demo.clear_generation_job(job_id)

    def test_request_generation_cancel_marks_job_cancelled(self):
        original_process = demo.process_parallel_candidates
        original_save = demo.save_demo_generation_artifacts

        async def fake_process_parallel_candidates(data_list, cancel_check=None, progress_callback=None, **kwargs):
            results = []
            total = 3
            if progress_callback:
                progress_callback(0, total, 1)
            for idx in range(total):
                await asyncio.sleep(0.02)
                if cancel_check and cancel_check():
                    break
                results.append(
                    {
                        "candidate_id": idx,
                        "task_name": "diagram",
                        "dataset_name": "PaperBananaBench",
                        "exp_mode": "demo_planner_critic",
                        "eval_image_field": "target_diagram_desc0_base64_jpg",
                        "target_diagram_desc0_base64_jpg": _build_png_base64(),
                    }
                )
                if progress_callback:
                    progress_callback(len(results), total, 1)
            return results, 1

        def fake_save_demo_generation_artifacts(**kwargs):
            return {
                "summary": {"total_candidates": len(kwargs["results"])},
                "failures": [],
                "json_file": "D:/tmp/cancelled_generation.json",
                "bundle_file": "D:/tmp/cancelled_generation.bundle.json",
                "manifest": {},
            }

        demo.process_parallel_candidates = fake_process_parallel_candidates
        demo.save_demo_generation_artifacts = fake_save_demo_generation_artifacts
        job_id = None
        try:
            job_id = demo.start_generation_background_job(
                dataset_name="PaperBananaBench",
                task_name="diagram",
                exp_mode="demo_planner_critic",
                retrieval_setting="none",
                curated_profile="default",
                provider="gemini",
                api_key="local-test-key",
                model_name="gemini-3.1-flash-lite-preview",
                image_model_name="gemini-3.1-flash-image-preview",
                concurrency_mode="manual",
                max_concurrent=1,
                num_candidates=3,
                max_critic_rounds=1,
                aspect_ratio="16:9",
                image_resolution="2K",
                content="paper method",
                visual_intent="draw a pipeline",
            )
            time.sleep(0.03)
            demo.request_generation_job_cancel(job_id)
            snapshot = self._wait_for_terminal_snapshot(job_id)

            self.assertEqual(snapshot["status"], "cancelled")
            self.assertTrue(snapshot["cancel_requested"])
            self.assertLess(len(snapshot["results"]), 3)
        finally:
            demo.process_parallel_candidates = original_process
            demo.save_demo_generation_artifacts = original_save
            if job_id:
                demo.clear_generation_job(job_id)

    def test_stage_candidate_for_refine_stores_session_image(self):
        result = {
            "target_diagram_desc0_base64_jpg": _build_png_base64(),
        }

        success = demo.stage_candidate_for_refine(
            result,
            candidate_id=7,
            exp_mode="demo_planner_critic",
            task_name="diagram",
        )

        self.assertTrue(success)
        self.assertTrue(demo.st.session_state["refine_staged_image_bytes"])
        self.assertEqual(demo.st.session_state["refine_staged_source_label"], "候选方案 7")

    def test_load_generation_history_snapshot_reads_bundle_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_path = Path(tmp_dir) / "history.bundle.json"
            results = [
                {
                    "candidate_id": 0,
                    "dataset_name": "CustomBench",
                    "task_name": "plot",
                    "exp_mode": "demo_planner_critic",
                    "eval_image_field": "target_plot_desc0_base64_jpg",
                    "target_plot_desc0_base64_jpg": _build_png_base64(),
                }
            ]
            manifest = build_run_manifest(
                producer="demo",
                dataset_name="CustomBench",
                task_name="plot",
                exp_mode="demo_planner_critic",
                provider="gemini",
                model_name="text-model",
                image_model_name="",
                concurrency_mode="manual",
                max_concurrent=2,
                max_critic_rounds=0,
                result_count=1,
                extra={
                    "requested_candidates": 4,
                    "effective_concurrent": 2,
                    "run_status": "completed",
                },
            )
            write_result_bundle(bundle_path, results, manifest=manifest)

            snapshot = demo.load_generation_history_snapshot(bundle_path)

            self.assertEqual(snapshot["dataset_name"], "CustomBench")
            self.assertEqual(snapshot["task_name"], "plot")
            self.assertEqual(snapshot["requested_candidates"], 4)
            self.assertEqual(snapshot["effective_concurrent"], 2)
            self.assertEqual(snapshot["bundle_file"], str(bundle_path))

    def test_list_demo_bundle_files_reads_latest_history_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results_root = Path(tmp_dir) / "results" / "demo" / "diagram"
            results_root.mkdir(parents=True, exist_ok=True)
            older_path = results_root / "older.bundle.json"
            newer_path = results_root / "newer.bundle.json"
            payload = {
                "schema": "paperbanana.result_bundle",
                "schema_version": 1,
                "manifest": {
                    "dataset_name": "PaperBananaBench",
                    "task_name": "diagram",
                    "exp_mode": "demo_planner_critic",
                    "provider": "gemini",
                    "result_count": 0,
                },
                "summary": {},
                "failures": [],
                "results": [],
            }
            older_path.write_text(json.dumps(payload), encoding="utf-8")
            time.sleep(0.02)
            newer_path.write_text(json.dumps(payload), encoding="utf-8")
            original_get_root = demo.get_demo_results_root
            demo.get_demo_results_root = lambda: Path(tmp_dir) / "results" / "demo"
            try:
                bundle_files = demo.list_demo_bundle_files("diagram", limit=5)
            finally:
                demo.get_demo_results_root = original_get_root

            self.assertEqual(bundle_files[0].name, "newer.bundle.json")
            self.assertEqual(bundle_files[1].name, "older.bundle.json")


if __name__ == "__main__":
    unittest.main()
