import unittest

from utils.pipeline_state import (
    PipelineState,
    build_render_stage_entries,
    collect_parse_error_round_keys,
    detect_task_type_from_result,
    find_final_stage_keys,
    get_render_options,
)


class PipelineStateTest(unittest.TestCase):
    def test_find_final_stage_keys_prefers_eval_image_field(self):
        result = {
            "eval_image_field": "target_diagram_critic_desc1_base64_jpg",
            "target_diagram_critic_desc1_base64_jpg": "abc",
        }

        image_key, desc_key = find_final_stage_keys(result, "diagram", "demo_full")

        self.assertEqual(image_key, "target_diagram_critic_desc1_base64_jpg")
        self.assertEqual(desc_key, "target_diagram_critic_desc1")

    def test_collect_parse_error_round_keys(self):
        result = {
            "target_plot_critic_status0": "ok",
            "target_plot_critic_status1": "parse_error",
            "target_diagram_critic_status3": "parse_error",
        }

        self.assertEqual(
            collect_parse_error_round_keys(result),
            ["target_diagram_critic_status3", "target_plot_critic_status1"],
        )

    def test_get_render_options_uses_additional_info(self):
        options = get_render_options(
            {
                "additional_info": {
                    "rounded_ratio": "16:9",
                    "image_resolution": "4K",
                }
            },
            default_aspect_ratio="1:1",
            default_image_resolution="2K",
        )

        self.assertEqual(options.aspect_ratio, "16:9")
        self.assertEqual(options.image_resolution, "4K")

    def test_pipeline_state_round_accessor(self):
        payload = {}
        state = PipelineState(payload, "plot")
        state.current_critic_round = 2

        self.assertEqual(state.current_critic_round, 2)
        self.assertEqual(payload["current_critic_round"], 2)

    def test_detect_task_type_from_wrapped_payload(self):
        payload = {
            "task_name": "plot",
            "results": [
                {
                    "candidate_id": 0,
                    "task_name": "plot",
                    "target_plot_desc0": "line chart",
                }
            ],
        }

        self.assertEqual(detect_task_type_from_result(payload), "plot")

    def test_find_final_stage_keys_uses_registry_base_render_source(self):
        result = {
            "exp_mode": "dev_planner_stylist",
            "target_diagram_desc0_base64_jpg": "planner",
            "target_diagram_stylist_desc0_base64_jpg": "stylist",
        }

        image_key, desc_key = find_final_stage_keys(result, "diagram", "dev_planner_stylist")

        self.assertEqual(image_key, "target_diagram_stylist_desc0_base64_jpg")
        self.assertEqual(desc_key, "target_diagram_stylist_desc0")

    def test_build_render_stage_entries_follows_pipeline_contract(self):
        result = {
            "exp_mode": "dev_full",
            "pipeline_spec": {
                "exp_mode": "dev_full",
            },
            "target_plot_desc0_base64_jpg": "planner",
            "target_plot_desc0": "planner desc",
            "target_plot_desc0_code": "print('planner')",
            "target_plot_stylist_desc0_base64_jpg": "stylist",
            "target_plot_stylist_desc0": "stylist desc",
            "target_plot_stylist_desc0_code": "print('stylist')",
            "target_plot_critic_desc1_base64_jpg": "critic",
            "target_plot_critic_desc1": "critic desc",
            "target_plot_critic_desc1_code": "print('critic')",
            "target_plot_critic_suggestions1": "Refine annotations.",
        }

        stages = build_render_stage_entries(result, "plot", "dev_full")

        self.assertEqual(
            [stage["stage_name"] for stage in stages],
            ["planner", "stylist", "critic"],
        )
        self.assertEqual(stages[0]["code_key"], "target_plot_desc0_code")
        self.assertEqual(stages[1]["code_key"], "target_plot_stylist_desc0_code")
        self.assertEqual(stages[2]["suggestions_key"], "target_plot_critic_suggestions1")


if __name__ == "__main__":
    unittest.main()
