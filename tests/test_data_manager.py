"""Tests for DatasetManager lazy-download, checksum verification, and caching."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import paperbanana_cn.data.manager as manager_mod
from paperbanana_cn.data.manager import (
    DatasetManager,
    _merge_index,
    _verify_sha256,
    resolve_reference_path,
)


@pytest.fixture()
def tmp_cache(tmp_path):
    """Provide a temporary cache directory with a DatasetManager."""
    return DatasetManager(cache_dir=tmp_path)


# ── _merge_index ──────────────────────────────────────────────────────


class TestMergeIndex:
    def test_merge_into_empty(self, tmp_path):
        idx = tmp_path / "index.json"
        examples = [
            {"id": "a", "category": "cat1"},
            {"id": "b", "category": "cat2"},
        ]
        count = _merge_index(idx, examples)
        assert count == 2
        data = json.loads(idx.read_text())
        assert data["metadata"]["total_examples"] == 2
        assert {e["id"] for e in data["examples"]} == {"a", "b"}

    def test_merge_deduplicates_by_id(self, tmp_path):
        idx = tmp_path / "index.json"
        _merge_index(idx, [{"id": "a", "category": "old"}, {"id": "b", "category": "keep"}])
        count = _merge_index(idx, [{"id": "a", "category": "new"}, {"id": "c", "category": "c"}])
        assert count == 3
        data = json.loads(idx.read_text())
        ids = {e["id"] for e in data["examples"]}
        assert ids == {"a", "b", "c"}
        a_entry = next(e for e in data["examples"] if e["id"] == "a")
        assert a_entry["category"] == "new"

    def test_merge_updates_categories(self, tmp_path):
        idx = tmp_path / "index.json"
        _merge_index(idx, [{"id": "x", "category": "alpha"}])
        _merge_index(idx, [{"id": "y", "category": "beta"}])
        data = json.loads(idx.read_text())
        assert sorted(data["metadata"]["categories"]) == ["alpha", "beta"]

    def test_merge_preserves_examples_without_id(self, tmp_path):
        idx = tmp_path / "index.json"
        _merge_index(idx, [{"id": "a", "category": "cat1"}, {"category": "no_id"}])
        count = _merge_index(idx, [{"category": "also_no_id"}])
        assert count == 3
        data = json.loads(idx.read_text())
        no_id_entries = [e for e in data["examples"] if "id" not in e]
        assert len(no_id_entries) == 2

    def test_merge_handles_corrupt_existing(self, tmp_path):
        idx = tmp_path / "index.json"
        idx.write_text("not json")
        count = _merge_index(idx, [{"id": "a", "category": "c"}])
        assert count == 1


# ── _verify_sha256 ────────────────────────────────────────────────────


class TestVerifySha256:
    def test_matching_checksum_passes(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"hello world")
        _verify_sha256(f, hashlib.sha256(b"hello world").hexdigest())

    def test_mismatch_raises_runtime_error(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"hello world")
        with pytest.raises(RuntimeError, match="SHA256 mismatch"):
            _verify_sha256(f, "0" * 64)


# ── DatasetManager.is_downloaded ──────────────────────────────────────


class TestIsDownloaded:
    def test_false_when_no_info_file(self, tmp_cache):
        assert not tmp_cache.is_downloaded()

    def test_true_with_datasets_marker(self, tmp_cache):
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache.info_path.write_text(
            json.dumps(
                {
                    "datasets": ["full_bench"],
                    "version": "1.0.0",
                }
            )
        )
        assert tmp_cache.is_downloaded()

    def test_back_compat_old_format(self, tmp_cache):
        """Old dataset_info.json without 'datasets' key but with a top-level source."""
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache.info_path.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "source": (
                        "https://huggingface.co/datasets/dwzhu/PaperBananaBench"
                        "/resolve/main/PaperBananaBench.zip"
                    ),
                }
            )
        )
        assert tmp_cache.is_downloaded()

    def test_legacy_cache_index_only(self, tmp_cache):
        """Caches with index.json but no dataset_info.json count as downloaded."""
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache.index_path.write_text(
            json.dumps(
                {
                    "metadata": {},
                    "examples": [{"id": "a"}],
                }
            )
        )
        assert tmp_cache.is_downloaded()

    def test_false_with_corrupt_info(self, tmp_cache):
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache.info_path.write_text("not json")
        assert not tmp_cache.is_downloaded()


# ── DatasetManager._record_dataset ────────────────────────────────────


class TestRecordDataset:
    def test_records_dataset(self, tmp_cache):
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache._record_dataset("full_bench", "1.0.0", "https://example.com", 298)
        info = json.loads(tmp_cache.info_path.read_text())
        assert "full_bench" in info["datasets"]
        assert info["example_count"] == 298
        assert info["dataset_meta"]["full_bench"]["version"] == "1.0.0"
        assert info["dataset_meta"]["full_bench"]["source"] == "https://example.com"

    def test_no_top_level_version_or_source(self, tmp_cache):
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache._record_dataset("full_bench", "2.0.0", "https://bench.example.com", 294)
        info = json.loads(tmp_cache.info_path.read_text())
        assert "version" not in info
        assert "source" not in info
        assert info["dataset_meta"]["full_bench"]["source"] == "https://bench.example.com"

    def test_back_compat_upgrade(self, tmp_cache):
        """Recording over an old-format info upgrades it to include the datasets list."""
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache.info_path.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "source": "https://old.example.com/PaperBananaBench.zip",
                }
            )
        )
        tmp_cache._record_dataset("full_bench", "1.0.0", "https://example.com", 298)
        info = json.loads(tmp_cache.info_path.read_text())
        assert info["datasets"] == ["full_bench"]


# ── DatasetManager.download ──────────────────────────────────────────


class TestDownload:
    @staticmethod
    def _make_bench_zip(zip_dest: Path):
        """Create a minimal fake PaperBananaBench.zip (no network).

        Only the top-level ``PaperBananaBench/`` directory matters here —
        the actual import is stubbed via ``_import_from_bench``.
        """
        import zipfile

        with zipfile.ZipFile(zip_dest, "w") as zf:
            zf.writestr("PaperBananaBench/.keep", "")

    def test_download_has_no_dataset_param(self):
        """The curated/full_bench split is gone — download() takes no dataset arg."""
        sig = inspect.signature(DatasetManager.download)
        assert "dataset" not in sig.parameters

    def test_url_points_at_github_mirror(self):
        assert manager_mod.DATASET_URL == (
            "https://github.com/llmsresearch/paperbanana/releases/download/"
            "bench-data-v1/PaperBananaBench.zip"
        )
        assert manager_mod.DATASET_RELEASE_TAG == "bench-data-v1"
        assert len(manager_mod.DATASET_SHA256) == 64

    def test_skip_when_already_cached(self, tmp_cache):
        tmp_cache.reference_dir.mkdir(parents=True)
        # Write a cached index with 2 examples
        tmp_cache.index_path.write_text(
            json.dumps(
                {
                    "metadata": {},
                    "examples": [{"id": "a"}, {"id": "b"}],
                }
            )
        )
        tmp_cache.info_path.write_text(
            json.dumps(
                {
                    "datasets": ["full_bench"],
                    "version": "1.0.0",
                }
            )
        )
        count = tmp_cache.download()
        assert count == 2  # returns cached count, no download

    def test_sha256_mismatch_raises(self, tmp_cache, monkeypatch):
        """A corrupted/tampered archive must hard-fail before extraction."""
        monkeypatch.setattr(manager_mod, "DATASET_SHA256", "0" * 64)

        def fake_download(url, dest):
            dest.write_bytes(b"definitely not the real dataset")

        with patch("paperbanana_cn.data.manager._download_file", side_effect=fake_download):
            with pytest.raises(RuntimeError, match="SHA256 mismatch"):
                tmp_cache.download(force=True)

    def test_download_merges_and_records(self, tmp_cache, monkeypatch):
        """Entries already in the cache survive a fresh full-bench import."""
        # Seed cache with pre-existing entries
        tmp_cache.reference_dir.mkdir(parents=True)
        (tmp_cache.reference_dir / "images").mkdir()
        tmp_cache.index_path.write_text(
            json.dumps(
                {
                    "metadata": {},
                    "examples": [
                        {"id": "preexisting", "category": "extra"},
                        {"id": "overlap", "category": "old_cat"},
                    ],
                }
            )
        )

        # _import_from_bench returns examples that overlap + new ones
        bench_examples = [
            {"id": "overlap", "category": "bench_cat"},
            {"id": "bench_new", "category": "bench_cat"},
        ]

        def fake_download(url, dest):
            self._make_bench_zip(dest)
            # Make the checksum match the fake archive we just wrote
            monkeypatch.setattr(
                manager_mod, "DATASET_SHA256", hashlib.sha256(dest.read_bytes()).hexdigest()
            )

        with (
            patch("paperbanana_cn.data.manager._download_file", side_effect=fake_download),
            patch(
                "paperbanana_cn.data.manager._import_from_bench",
                return_value=bench_examples,
            ),
        ):
            count = tmp_cache.download(force=True)

        assert count == 3  # preexisting + overlap (updated) + bench_new
        data = json.loads(tmp_cache.index_path.read_text())
        ids = {e["id"] for e in data["examples"]}
        assert ids == {"preexisting", "overlap", "bench_new"}

        # overlap entry should be updated by the bench import (new wins)
        overlap = next(e for e in data["examples"] if e["id"] == "overlap")
        assert overlap["category"] == "bench_cat"

        # dataset_info should record the mirror + release tag
        info = json.loads(tmp_cache.info_path.read_text())
        assert info["datasets"] == ["full_bench"]
        meta = info["dataset_meta"]["full_bench"]
        assert meta["source"] == manager_mod.DATASET_URL
        assert meta["revision"] == manager_mod.DATASET_RELEASE_TAG

    def test_download_with_progress(self, tmp_cache, monkeypatch):
        bench_examples = [{"id": "p1", "category": "c"}]
        messages = []

        def fake_download(url, dest):
            self._make_bench_zip(dest)
            monkeypatch.setattr(
                manager_mod, "DATASET_SHA256", hashlib.sha256(dest.read_bytes()).hexdigest()
            )

        with (
            patch("paperbanana_cn.data.manager._download_file", side_effect=fake_download),
            patch(
                "paperbanana_cn.data.manager._import_from_bench",
                return_value=bench_examples,
            ),
        ):
            tmp_cache.download(
                force=True,
                progress_callback=lambda msg: messages.append(msg),
            )

        assert any("checksum" in m.lower() for m in messages)
        assert any("paperbananabench" in m.lower() for m in messages)


# ── resolve_reference_path ────────────────────────────────────────────


class TestResolveReferencePath:
    def test_explicit_settings_path_wins(self, tmp_path):
        result = resolve_reference_path("/custom/path", cache_dir=str(tmp_path))
        assert result == "/custom/path"

    def test_uses_cache_when_downloaded(self, tmp_path):
        ref_dir = tmp_path / "reference_sets"
        ref_dir.mkdir(parents=True)
        (ref_dir / "index.json").write_text(
            json.dumps(
                {
                    "metadata": {},
                    "examples": [{"id": "a"}],
                }
            )
        )
        (ref_dir / "dataset_info.json").write_text(
            json.dumps(
                {
                    "datasets": ["full_bench"],
                    "version": "1.0.0",
                }
            )
        )
        result = resolve_reference_path("data/reference_sets", cache_dir=str(tmp_path))
        assert result == str(ref_dir)

    def test_falls_back_to_builtin(self, tmp_path):
        result = resolve_reference_path("data/reference_sets", cache_dir=str(tmp_path))
        assert result == "data/reference_sets"


# ── DatasetManager.clear ──────────────────────────────────────────────


class TestClear:
    def test_clear_removes_cache(self, tmp_cache):
        tmp_cache.reference_dir.mkdir(parents=True)
        tmp_cache.info_path.write_text("{}")
        tmp_cache.clear()
        assert not tmp_cache.reference_dir.exists()

    def test_clear_noop_when_empty(self, tmp_cache):
        tmp_cache.clear()  # should not raise


class TestResolveImageUnicode:
    """NFD-extracted filenames must still resolve (issue #234)."""

    def test_nfd_filename_resolves_via_nfc_comparison(self, tmp_path):
        import unicodedata

        from paperbanana_cn.data.manager import _resolve_image

        images = tmp_path / "images"
        images.mkdir()
        # Name with U+2011 (non-breaking hyphen), written in NFD form as
        # macOS zip extraction produces.
        name_nfc = "VTON‑VLLM Aligning Modéls_diagram.jpg"
        nfd_name = unicodedata.normalize("NFD", name_nfc)
        (images / nfd_name).write_bytes(b"fake")

        resolved = _resolve_image(images, name_nfc)
        assert resolved is not None
        assert resolved.read_bytes() == b"fake"

    def test_exact_match_still_preferred(self, tmp_path):
        from paperbanana_cn.data.manager import _resolve_image

        images = tmp_path / "images"
        images.mkdir()
        (images / "plain.jpg").write_bytes(b"x")
        resolved = _resolve_image(images, "plain.jpg")
        assert resolved == images / "plain.jpg"

    def test_missing_image_returns_none(self, tmp_path):
        from paperbanana_cn.data.manager import _resolve_image

        images = tmp_path / "images"
        images.mkdir()
        assert _resolve_image(images, "nope.jpg") is None


class TestOfficialTestSplit:
    """Import + load round-trip for the official test split (issue #235)."""

    def _make_bench_dir(self, tmp_path):
        import json

        bench = tmp_path / "PaperBananaBench"
        for task in ("diagram", "plot"):
            (bench / task / "images").mkdir(parents=True)
        (bench / "diagram" / "images" / "fig1.jpg").write_bytes(b"img1")
        (bench / "diagram" / "test.json").write_text(
            json.dumps(
                [
                    {
                        "id": "d1",
                        "category": "vision",
                        "content": "methodology text",
                        "visual_intent": "Overview figure",
                        "path_to_gt_image": "fig1.jpg",
                        "split": "test",
                        "additional_info": {"rounded_ratio": "16:9", "width": 1600, "height": 900},
                    }
                ]
            ),
            encoding="utf-8",
        )
        (bench / "plot" / "images" / "p1.jpg").write_bytes(b"img2")
        (bench / "plot" / "test.json").write_text(
            json.dumps(
                [
                    {
                        "id": "p1",
                        "category": "bar",
                        "content": {"x": [1, 2], "y": [3, 4]},
                        "visual_intent": "Bar chart",
                        "path_to_gt_image": "p1.jpg",
                        "difficulty": "easy",
                        "additional_info": {"rounded_ratio": "3:2", "gt_code": "plt.bar(x, y)"},
                    }
                ]
            ),
            encoding="utf-8",
        )
        return bench

    def test_import_and_load_round_trip(self, tmp_path):
        from paperbanana_cn.data.manager import DatasetManager, _import_test_split

        bench = self._make_bench_dir(tmp_path)
        dm = DatasetManager(cache_dir=tmp_path / "cache")
        count = _import_test_split(bench, "both", dm.test_split_dir)
        assert count == 2

        diagram_cases = dm.load_test_split("diagram")
        assert len(diagram_cases) == 1
        case = diagram_cases[0]
        assert case.id == "d1"
        assert case.aspect_ratio == "16:9"
        assert case.task == "diagram"
        assert Path(case.gt_image_path).exists()

        plot_cases = dm.load_test_split("plot")
        assert plot_cases[0].gt_code == "plt.bar(x, y)"
        assert plot_cases[0].difficulty == "easy"
        assert plot_cases[0].raw_data == {"x": [1, 2], "y": [3, 4]}

    def test_load_missing_split_raises_with_hint(self, tmp_path):
        from paperbanana_cn.data.manager import DatasetManager

        dm = DatasetManager(cache_dir=tmp_path / "cache")
        with pytest.raises(RuntimeError, match="data download"):
            dm.load_test_split("diagram")

    def test_load_rejects_unknown_task(self, tmp_path):
        from paperbanana_cn.data.manager import DatasetManager

        dm = DatasetManager(cache_dir=tmp_path / "cache")
        with pytest.raises(ValueError, match="diagram"):
            dm.load_test_split("poster")
