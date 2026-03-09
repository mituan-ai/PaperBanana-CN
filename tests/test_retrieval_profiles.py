import json
import tempfile
import unittest
from pathlib import Path

from utils.retrieval_profiles import load_curated_reference_profile


class CuratedReferenceProfileTest(unittest.TestCase):
    def _build_dataset_dir(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        work_dir = Path(temp_dir.name)
        dataset_dir = work_dir / "data" / "PaperBananaBench" / "diagram"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir, dataset_dir

    def test_id_only_profile_joins_against_reference_pool(self):
        temp_dir, dataset_dir = self._build_dataset_dir()
        self.addCleanup(temp_dir.cleanup)
        (dataset_dir / "ref.json").write_text(
            json.dumps(
                [
                    {"id": "ref_1", "visual_intent": "Pipeline", "content": "Step A to Step B"},
                    {"id": "ref_2", "visual_intent": "Ablation", "content": "Compare variants"},
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        profile_dir = dataset_dir / "manual_profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "default.json").write_text(
            json.dumps({"selected_ids": ["ref_1", "missing_ref"]}, ensure_ascii=False),
            encoding="utf-8",
        )

        profile = load_curated_reference_profile(
            "PaperBananaBench",
            "diagram",
            work_dir=dataset_dir.parent.parent.parent,
        )

        self.assertEqual(profile.profile_name, "default")
        self.assertEqual(profile.selected_ids, ["ref_1"])
        self.assertEqual([item["id"] for item in profile.examples], ["ref_1"])
        self.assertEqual(profile.missing_ids, ["missing_ref"])
        self.assertEqual(profile.source_path.name, "default.json")

    def test_default_profile_falls_back_to_legacy_manual_file(self):
        temp_dir, dataset_dir = self._build_dataset_dir()
        self.addCleanup(temp_dir.cleanup)
        legacy_examples = [
            {"id": "legacy_1", "visual_intent": "Legacy example", "content": "Legacy content"},
            {"id": "legacy_2", "visual_intent": "Legacy example 2", "content": "More content"},
        ]
        (dataset_dir / "agent_selected_12.json").write_text(
            json.dumps(legacy_examples, ensure_ascii=False),
            encoding="utf-8",
        )

        profile = load_curated_reference_profile(
            "PaperBananaBench",
            "diagram",
            work_dir=dataset_dir.parent.parent.parent,
        )

        self.assertEqual(profile.profile_name, "default")
        self.assertEqual(profile.selected_ids, ["legacy_1", "legacy_2"])
        self.assertEqual([item["id"] for item in profile.examples], ["legacy_1", "legacy_2"])
        self.assertTrue(profile.is_legacy_file)
        self.assertEqual(profile.source_path.name, "agent_selected_12.json")


if __name__ == "__main__":
    unittest.main()
