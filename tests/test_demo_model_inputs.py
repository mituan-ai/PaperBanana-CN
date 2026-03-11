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


class _FakeInteractiveStreamlit:
    def __init__(self):
        self.session_state = {}

    def selectbox(self, label, options, index=0, key=None, help=None):
        if key not in self.session_state:
            self.session_state[key] = options[index]
        return self.session_state[key]

    def text_input(self, label, value="", key=None, help=None, **kwargs):
        if key not in self.session_state:
            self.session_state[key] = value
        return self.session_state[key]


class DemoModelInputTest(unittest.TestCase):
    def setUp(self):
        self.original_streamlit = demo.st
        self.fake_streamlit = _FakeInteractiveStreamlit()
        demo.st = self.fake_streamlit

    def tearDown(self):
        demo.st = self.original_streamlit

    def test_custom_model_value_initializes_selector_and_text_buffer(self):
        self.fake_streamlit.session_state["model_value"] = "vendor/custom-text-model"

        resolved = demo.render_preset_or_custom_model_input(
            "文本模型",
            ["preset-a", "preset-b"],
            value_key="model_value",
            selector_key="model_selector",
            custom_value_key="model_custom",
            default_value="preset-a",
            select_help="help",
        )

        self.assertEqual(resolved, "vendor/custom-text-model")
        self.assertEqual(
            self.fake_streamlit.session_state["model_selector"],
            demo.CUSTOM_MODEL_OPTION,
        )
        self.assertEqual(
            self.fake_streamlit.session_state["model_custom"],
            "vendor/custom-text-model",
        )

    def test_custom_selector_uses_manual_input_value(self):
        self.fake_streamlit.session_state.update(
            {
                "model_value": "preset-a",
                "model_selector": demo.CUSTOM_MODEL_OPTION,
                "model_custom": "vendor/manual-image-model",
            }
        )

        resolved = demo.render_preset_or_custom_model_input(
            "图像模型",
            ["preset-a", "preset-b"],
            value_key="model_value",
            selector_key="model_selector",
            custom_value_key="model_custom",
            default_value="preset-a",
            select_help="help",
        )

        self.assertEqual(resolved, "vendor/manual-image-model")
        self.assertEqual(
            self.fake_streamlit.session_state["model_value"],
            "vendor/manual-image-model",
        )

    def test_initialize_curated_profile_state_separates_widget_key_from_canonical_key(self):
        self.fake_streamlit.session_state["curated_profile"] = " paper profile "

        normalized = demo.initialize_curated_profile_state(
            profile_key="curated_profile",
            input_key="curated_profile_input",
        )

        self.assertEqual(normalized, "paper-profile")
        self.assertEqual(
            self.fake_streamlit.session_state["curated_profile"],
            "paper-profile",
        )
        self.assertEqual(
            self.fake_streamlit.session_state["curated_profile_input"],
            "paper-profile",
        )

    def test_resolve_curated_profile_input_updates_only_canonical_key(self):
        self.fake_streamlit.session_state["curated_profile"] = "default"
        self.fake_streamlit.session_state["curated_profile_input"] = " custom profile "

        normalized = demo.resolve_curated_profile_input(
            self.fake_streamlit.session_state["curated_profile_input"],
            profile_key="curated_profile",
        )

        self.assertEqual(normalized, "custom-profile")
        self.assertEqual(
            self.fake_streamlit.session_state["curated_profile"],
            "custom-profile",
        )
        self.assertEqual(
            self.fake_streamlit.session_state["curated_profile_input"],
            " custom profile ",
        )

    def test_hydrate_api_key_session_state_restores_local_default_when_blank(self):
        self.fake_streamlit.session_state["tab1_api_key"] = ""

        restored = demo.hydrate_api_key_session_state(
            session_key="tab1_api_key",
            provider_defaults={"api_key_default": "local-google-key"},
        )

        self.assertEqual(restored, "local-google-key")
        self.assertEqual(
            self.fake_streamlit.session_state["tab1_api_key"],
            "local-google-key",
        )
