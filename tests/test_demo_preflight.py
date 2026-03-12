import importlib
import sys
import types
import unittest
from pathlib import Path


if "streamlit" not in sys.modules:
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.set_page_config = lambda *args, **kwargs: None
    fake_streamlit.session_state = {}
    sys.modules["streamlit"] = fake_streamlit

demo = importlib.import_module("demo")


class DemoPreflightTest(unittest.TestCase):
    def test_preflight_report_flags_parse_errors_without_input_required_messages(self):
        report = demo.build_generation_preflight_report(
            task_name="plot",
            input_content="",
            visual_intent="",
            content_for_generation="",
            allow_raw_plot_input=False,
            num_candidates=3,
            effective_settings={
                "retrieval_setting": "auto",
                "max_critic_rounds": 1,
                "exp_mode": "demo_planner_critic",
                "api_key": "",
            },
            retrieval_ref_path=Path("D:/PaperBanana/data/PaperBananaBench/plot/missing_ref.json"),
            resolved_profile_path=None,
            generation_is_running=False,
        )

        self.assertEqual(len(report["errors"]), 1)
        self.assertTrue(any("plot 输入尚未通过结构化解析" in item for item in report["errors"]))
        self.assertTrue(any("API Key" in item for item in report["warnings"]))
        self.assertTrue(any("当前参数" in item for item in report["notes"]))
        self.assertTrue(any("未找到参考样例库" in item for item in report["warnings"]))

    def test_build_generation_effective_settings_preserves_manual_advanced_values(self):
        effective = demo._build_generation_effective_settings(
            {
                "exp_mode": "demo_planner_critic",
                "retrieval_setting": "none",
                "max_critic_rounds": 0,
                "image_resolution": "2K",
            },
            task_name="diagram",
        )

        self.assertEqual(effective["exp_mode"], "demo_planner_critic")
        self.assertEqual(effective["retrieval_setting"], "none")
        self.assertEqual(effective["max_critic_rounds"], 0)
        self.assertEqual(effective["image_resolution"], "2K")


if __name__ == "__main__":
    unittest.main()
