import unittest

from utils.plot_input_utils import parse_plot_input_text


class PlotInputUtilsTest(unittest.TestCase):
    def test_parse_json_records(self):
        parsed = parse_plot_input_text('[{"x": 1, "y": 2}, {"x": 2, "y": 3}]')

        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["format"], "json")
        self.assertEqual(parsed["row_count"], 2)
        self.assertEqual(parsed["columns"], ["x", "y"])
        self.assertEqual(parsed["normalized_content"][0]["x"], 1)

    def test_parse_csv_records(self):
        parsed = parse_plot_input_text("method,score\nPaperBanana,62.1\nBaseline,58.2\n")

        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["format"], "csv")
        self.assertEqual(parsed["row_count"], 2)
        self.assertEqual(parsed["normalized_content"][1]["method"], "Baseline")

    def test_parse_markdown_table(self):
        parsed = parse_plot_input_text(
            "| method | score |\n| --- | --- |\n| PaperBanana | 62.1 |\n| Baseline | 58.2 |\n"
        )

        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["format"], "markdown_table")
        self.assertEqual(parsed["row_count"], 2)
        self.assertEqual(parsed["normalized_content"][0]["score"], 62.1)

    def test_invalid_payload_returns_error(self):
        parsed = parse_plot_input_text("method score PaperBanana 62.1")

        self.assertFalse(parsed["ok"])
        self.assertEqual(parsed["format"], "raw_text")
        self.assertIn("JSON", parsed["error"])


if __name__ == "__main__":
    unittest.main()
