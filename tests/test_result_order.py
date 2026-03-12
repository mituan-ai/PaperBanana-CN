import unittest

from utils.result_order import (
    format_candidate_display_label,
    get_candidate_display_index,
    get_candidate_id,
    prepare_input_payload,
    sort_results_stably,
)


class ResultOrderTest(unittest.TestCase):
    def test_prepare_input_payload_backfills_candidate_metadata(self):
        payload = prepare_input_payload({"id": "sample_0"}, 7)

        self.assertEqual(payload["input_index"], 7)
        self.assertEqual(payload["candidate_id"], 7)
        self.assertEqual(payload["id"], "sample_0")

    def test_sort_results_stably_prefers_input_index(self):
        results = [
            {"candidate_id": 4, "input_index": 2, "id": "c"},
            {"candidate_id": 2, "input_index": 0, "id": "a"},
            {"candidate_id": 3, "input_index": 1, "id": "b"},
        ]

        ordered = sort_results_stably(results)

        self.assertEqual([item["id"] for item in ordered], ["a", "b", "c"])

    def test_get_candidate_id_falls_back_cleanly(self):
        self.assertEqual(get_candidate_id({"candidate_id": 5}, "x"), 5)
        self.assertEqual(get_candidate_id({"input_index": 8}, "x"), 8)
        self.assertEqual(get_candidate_id({"id": "sample_1"}, "x"), "sample_1")
        self.assertEqual(get_candidate_id({}, "x"), "x")

    def test_candidate_display_helpers_use_one_based_human_labels(self):
        result = {"candidate_id": 7}

        self.assertEqual(get_candidate_display_index(result, fallback_index=0), 8)
        self.assertEqual(
            format_candidate_display_label(result, fallback_index=0),
            "候选 08",
        )


if __name__ == "__main__":
    unittest.main()
