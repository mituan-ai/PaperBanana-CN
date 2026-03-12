import importlib
import sys
import types
import unittest


if "streamlit" not in sys.modules:
    fake_streamlit = types.ModuleType("streamlit")
    sys.modules["streamlit"] = fake_streamlit

fake_streamlit = sys.modules["streamlit"]
if not hasattr(fake_streamlit, "set_page_config"):
    fake_streamlit.set_page_config = lambda *args, **kwargs: None
if not hasattr(fake_streamlit, "cache_data"):
    def _cache_data(fn=None, **kwargs):
        if fn is None:
            return lambda real_fn: real_fn
        return fn
    fake_streamlit.cache_data = _cache_data
if not hasattr(fake_streamlit, "session_state"):
    fake_streamlit.session_state = {}


show_pipeline_evolution = importlib.import_module("visualize.show_pipeline_evolution")
show_referenced_eval = importlib.import_module("visualize.show_referenced_eval")
viewer_helpers = importlib.import_module("visualize.viewer_helpers")


class ViewerHelperTest(unittest.TestCase):
    def test_shared_viewer_helper_search_matches_candidate_id_and_caption(self):
        item = {
            "candidate_id": 6,
            "filename": "candidate_06.json",
            "brief_desc": "Signal pathway overview",
        }

        self.assertEqual(viewer_helpers.get_result_identifier(item, 0), "6")
        self.assertTrue(viewer_helpers.matches_result_search(item, "06", 0))
        self.assertTrue(viewer_helpers.matches_result_search(item, "signal", 0))
        self.assertFalse(viewer_helpers.matches_result_search(item, "missing", 0))

    def test_pipeline_viewer_identifier_prefers_candidate_id(self):
        item = {"candidate_id": 3, "id": "legacy-id"}

        identifier = show_pipeline_evolution.get_result_identifier(item, 0)

        self.assertEqual(identifier, "3")

    def test_pipeline_viewer_search_matches_candidate_id_and_legacy_id(self):
        item = {"candidate_id": 4, "id": "paper-sample-4", "visual_intent": "Draw the pipeline"}

        self.assertTrue(show_pipeline_evolution.matches_result_search(item, "4", 0))
        self.assertTrue(show_pipeline_evolution.matches_result_search(item, "paper-sample", 0))
        self.assertTrue(show_pipeline_evolution.matches_result_search(item, "pipeline", 0))
        self.assertFalse(show_pipeline_evolution.matches_result_search(item, "missing", 0))

    def test_pipeline_viewer_prefers_latest_critic_suggestions(self):
        item = {
            "task_name": "diagram",
            "target_diagram_critic_desc0_base64_jpg": "preview-a",
            "target_diagram_critic_desc1_base64_jpg": "preview-b",
            "target_diagram_critic_suggestions0": "old suggestions",
            "target_diagram_critic_suggestions1": "latest suggestions",
            "critique0": "legacy critique",
        }

        notes = show_pipeline_evolution.get_latest_review_notes(item)

        self.assertEqual(notes, "latest suggestions")

    def test_eval_viewer_prefers_candidate_id_identifier_and_latest_suggestions(self):
        item = {
            "candidate_id": 2,
            "id": "legacy-id",
            "task_name": "plot",
            "target_plot_critic_desc0_base64_jpg": "preview-a",
            "target_plot_critic_suggestions0": "tighten the layout",
            "suggestions_plot": "legacy suggestion",
        }

        identifier = show_referenced_eval.get_result_identifier(item, 0)
        suggestions = show_referenced_eval.get_latest_suggestions(item, "plot")

        self.assertEqual(identifier, "2")
        self.assertEqual(suggestions, "tighten the layout")


if __name__ == "__main__":
    unittest.main()
