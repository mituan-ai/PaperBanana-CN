import importlib
import sys
import types
import unittest


if "streamlit" not in sys.modules:
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.set_page_config = lambda *args, **kwargs: None
    fake_streamlit.session_state = {}
    sys.modules["streamlit"] = fake_streamlit

demo = importlib.import_module("demo")


class DemoWorkbenchStateTest(unittest.TestCase):
    def setUp(self):
        demo.st.session_state.clear()

    def test_generation_candidate_decision_filter_scopes(self):
        results = [
            {"candidate_id": 0},
            {"candidate_id": 1},
            {"candidate_id": 2},
        ]
        demo.set_generation_candidate_decision(0, "favorite")
        demo.set_generation_candidate_decision(1, "discarded")
        demo.set_generation_candidate_decision(2, "final")

        self.assertEqual(len(demo.filter_generation_results_by_scope(results, "全部候选")), 3)
        self.assertEqual(
            [item["candidate_id"] for item in demo.filter_generation_results_by_scope(results, "仅未淘汰")],
            [0, 2],
        )
        self.assertEqual(
            [item["candidate_id"] for item in demo.filter_generation_results_by_scope(results, "仅收藏")],
            [0, 2],
        )
        self.assertEqual(
            [item["candidate_id"] for item in demo.filter_generation_results_by_scope(results, "仅最终候选")],
            [2],
        )

    def test_setting_new_final_candidate_replaces_previous_final(self):
        demo.set_generation_candidate_decision(0, "final")
        demo.set_generation_candidate_decision(1, "final")

        self.assertEqual(demo.get_generation_candidate_decision(0), "default")
        self.assertEqual(demo.get_generation_candidate_decision(1), "final")

        demo.set_generation_candidate_decision(1, "discarded")
        self.assertEqual(demo.get_generation_candidate_decision(1), "discarded")
        self.assertEqual(demo.get_generation_final_candidate_token(), "")

    def test_append_refine_snapshot_to_version_history_creates_branch_versions(self):
        original_bytes = b"original-image"
        demo.stage_refine_source_image(
            original_bytes,
            input_mime_type="image/png",
            source_label="候选 01",
            default_prompt="保持语义不变",
        )
        parent_version_key = demo.ensure_refine_source_version(
            original_bytes,
            input_mime_type="image/png",
            source_label="候选 01",
        )
        demo.st.session_state["refine_active_version_key"] = parent_version_key

        created_keys = demo.append_refine_snapshot_to_version_history(
            {
                "created_at": "2026-03-12 18:00:00",
                "provider": "gemini",
                "image_model_name": "gemini-image",
                "resolution": "4K",
                "input_mime_type": "image/png",
                "original_image_bytes": original_bytes,
                "refined_images": [
                    {"index": 1, "bytes": b"refined-v1"},
                    {"index": 2, "bytes": b"refined-v2"},
                ],
            },
            edit_prompt="放大并优化布局",
        )

        self.assertEqual(len(created_keys), 2)
        self.assertEqual(demo.st.session_state["refine_active_version_key"], created_keys[0])
        history = demo.get_refine_version_history()
        child_nodes = [item for item in history if item.get("parent_version_key") == parent_version_key]
        self.assertEqual(len(child_nodes), 2)
        self.assertTrue(all(item.get("edit_prompt") == "放大并优化布局" for item in child_nodes))

    def test_append_refine_snapshot_prefers_selected_source_label(self):
        original_bytes = b"uploaded-image"
        demo.st.session_state["refine_staged_source_label"] = "候选 01"
        demo.st.session_state["refine_selected_source_label"] = "上传图像"

        created_keys = demo.append_refine_snapshot_to_version_history(
            {
                "created_at": "2026-03-12 19:00:00",
                "provider": "gemini",
                "image_model_name": "gemini-image",
                "resolution": "2K",
                "input_mime_type": "image/png",
                "original_image_bytes": original_bytes,
                "refined_images": [
                    {"index": 1, "bytes": b"refined-upload"},
                ],
            },
            edit_prompt="只做清晰度增强",
        )

        self.assertEqual(len(created_keys), 1)
        created_entry = demo.find_refine_version_entry(created_keys[0])
        self.assertIsNotNone(created_entry)
        self.assertEqual(created_entry.get("source_label"), "上传图像")

    def test_persist_generation_results_can_preserve_candidate_workspace(self):
        demo.st.session_state["generation_candidate_decisions"] = {"1": "favorite"}
        demo.st.session_state["generation_final_candidate_id"] = "2"

        demo.persist_generation_job_results(
            {
                "results": [{"candidate_id": 1}, {"candidate_id": 2}],
                "task_name": "diagram",
                "dataset_name": "PaperBananaBench",
                "exp_mode": "demo_planner_critic",
                "summary": {},
                "failures": [],
            },
            source_label="历史回放",
            reset_candidate_workspace=False,
        )

        self.assertEqual(demo.st.session_state["generation_candidate_decisions"], {"1": "favorite"})
        self.assertEqual(demo.st.session_state["generation_final_candidate_id"], "2")

    def test_complex_ui_state_round_trip_handles_version_history_bytes(self):
        payload = demo._serialize_ui_state_value(
            "refine_version_history",
            [
                {
                    "version_key": "v01",
                    "image_bytes": b"image-bytes",
                }
            ],
        )

        restored = demo._deserialize_ui_state_value("refine_version_history", payload)

        self.assertEqual(restored[0]["version_key"], "v01")
        self.assertEqual(restored[0]["image_bytes"], b"image-bytes")

    def test_apply_pending_generation_widget_state_updates_flushes_queue(self):
        demo.st.session_state["_pending_generation_widget_updates"] = {
            "tab1_exp_mode": "demo_planner_critic",
            "tab1_image_resolution": "2K",
        }

        demo._apply_pending_generation_widget_state_updates()

        self.assertEqual(demo.st.session_state["tab1_exp_mode"], "demo_planner_critic")
        self.assertEqual(demo.st.session_state["tab1_image_resolution"], "2K")
        self.assertNotIn("_pending_generation_widget_updates", demo.st.session_state)


if __name__ == "__main__":
    unittest.main()
