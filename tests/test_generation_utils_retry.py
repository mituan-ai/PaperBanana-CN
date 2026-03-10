import unittest

from utils import generation_utils


class GeminiRetryPolicyTest(unittest.TestCase):
    def test_text_pro_models_fall_back_to_flash_lite_then_flash(self):
        ladder = generation_utils._build_gemini_model_ladder(
            "gemini-3.1-pro-preview",
            is_image_request=False,
        )

        self.assertEqual(
            ladder,
            [
                "gemini-3.1-pro-preview",
                "gemini-3.1-flash-lite-preview",
                "gemini-3-flash-preview",
            ],
        )

    def test_image_pro_models_fall_back_to_flash_image(self):
        ladder = generation_utils._build_gemini_model_ladder(
            "gemini-3-pro-image-preview",
            is_image_request=True,
        )

        self.assertEqual(
            ladder,
            [
                "gemini-3-pro-image-preview",
                generation_utils.DEFAULT_GEMINI_IMAGE_FALLBACK_MODEL,
            ],
        )

    def test_stage_retry_budget_demotes_text_pro_after_first_cycle(self):
        self.assertEqual(
            generation_utils._stage_retry_budget(
                stage_model_name="gemini-3.1-pro-preview",
                primary_model_name="gemini-3.1-pro-preview",
                is_image_request=False,
                cycle_index=0,
                requested_attempts=5,
            ),
            2,
        )
        self.assertEqual(
            generation_utils._stage_retry_budget(
                stage_model_name="gemini-3.1-pro-preview",
                primary_model_name="gemini-3.1-pro-preview",
                is_image_request=False,
                cycle_index=1,
                requested_attempts=5,
            ),
            0,
        )

    def test_permanent_quota_block_uses_long_cooldown(self):
        cooldown = generation_utils._compute_cycle_cooldown_seconds(
            "429 RESOURCE_EXHAUSTED limit: 0 quota exceeded",
            retry_delay=5,
            cycle_index=0,
        )

        self.assertGreaterEqual(cooldown, 300.0)


if __name__ == "__main__":
    unittest.main()
