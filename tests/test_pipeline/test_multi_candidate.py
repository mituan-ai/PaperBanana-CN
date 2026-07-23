"""Tests for multi-candidate generation (--num-candidates, issue #237)."""

from __future__ import annotations

import json
import re

import pytest

pytest.importorskip("PIL", reason="PIL/Pillow required for pipeline image mock")
from pathlib import Path

from PIL import Image

from paperbanana_cn.core import pipeline as pipeline_mod
from paperbanana_cn.core.config import Settings
from paperbanana_cn.core.pipeline import PaperBananaPipeline
from paperbanana_cn.core.types import DiagramType, GenerationInput

# ── Shared mocks ─────────────────────────────────────────────────


class _MockVLM:
    name = "mock-vlm"
    model_name = "mock-model"

    def __init__(self, responses: list[str]):
        self._responses = responses
        self._idx = 0

    async def generate(self, *args, **kwargs):
        idx = min(self._idx, len(self._responses) - 1)
        self._idx += 1
        return self._responses[idx]


class _SeedRecordingImageGen:
    """Image-gen mock that records seeds and can fail for specific seeds."""

    name = "mock-image-gen"
    model_name = "mock-image-model"

    def __init__(self, fail_seeds: tuple[int | None, ...] = ()):
        self.seeds: list[int | None] = []
        self.fail_seeds = set(fail_seeds)

    async def generate(self, *args, **kwargs):
        seed = kwargs.get("seed")
        self.seeds.append(seed)
        if seed in self.fail_seeds:
            raise RuntimeError(f"image gen exploded for seed {seed}")
        return Image.new("RGB", (64, 64), color=(255, 255, 255))


def _make_settings(tmp_path, **overrides):
    defaults = dict(
        output_dir=str(tmp_path / "outputs"),
        reference_set_path=str(tmp_path / "empty_refs"),
        refinement_iterations=1,
        save_iterations=True,
        save_prompts=False,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _default_input():
    return GenerationInput(
        source_context="Test methodology text",
        communicative_intent="Test caption",
        diagram_type=DiagramType.METHODOLOGY,
    )


_ACCEPT_CRITIQUE = json.dumps({"critic_suggestions": [], "revised_description": None})


@pytest.fixture(autouse=True)
def _fast_retry(monkeypatch):
    """Replace _call_with_retry with a zero-wait version for fast tests."""

    async def _fast_call_with_retry(label, fn, *args, max_attempts=3, **kwargs):
        last_exc = None
        for attempt_num in range(1, max_attempts + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt_num >= max_attempts:
                    raise
        raise last_exc  # unreachable but satisfies type checker

    monkeypatch.setattr(pipeline_mod, "_call_with_retry", _fast_call_with_retry)


def _make_pipeline(settings, image_gen=None):
    vlm = _MockVLM(responses=["Plan description", "Styled description", _ACCEPT_CRITIQUE])
    return PaperBananaPipeline(
        settings=settings,
        vlm_client=vlm,
        image_gen_fn=image_gen or _SeedRecordingImageGen(),
    )


# ── Fan-out produces N candidate dirs and metadata entries ────────


@pytest.mark.asyncio
async def test_fanout_produces_candidate_dirs_and_metadata(tmp_path):
    settings = _make_settings(tmp_path, num_candidates=3)
    pipeline = _make_pipeline(settings)

    result = await pipeline.generate(_default_input())

    run_dir = Path(settings.output_dir) / pipeline.run_id
    for idx in (1, 2, 3):
        cand_dir = run_dir / "candidates" / f"cand_{idx}"
        assert (cand_dir / "final_output.png").exists()
        assert (cand_dir / "iter_1" / "details.json").exists()

    # Run-root final output is still produced (primary = candidate 1)
    assert result.image_path == str(run_dir / "final_output.png")
    assert Path(result.image_path).exists()

    metadata = json.loads((run_dir / "metadata.json").read_text())
    assert metadata["num_candidates"] == 3
    assert metadata["primary_candidate"] == 1
    candidates = metadata["candidates"]
    assert [c["index"] for c in candidates] == [1, 2, 3]
    for cand in candidates:
        assert cand["error"] is None
        assert cand["iterations"] == 1
        assert cand["critic_satisfied"] is True
        assert Path(cand["image_path"]).exists()


# ── Single-candidate runs keep the existing layout ────────────────


@pytest.mark.asyncio
async def test_single_candidate_has_no_candidates_metadata(tmp_path):
    settings = _make_settings(tmp_path)
    pipeline = _make_pipeline(settings)

    result = await pipeline.generate(_default_input())

    run_dir = Path(settings.output_dir) / pipeline.run_id
    assert not (run_dir / "candidates").exists()
    assert "candidates" not in result.metadata
    assert Path(result.image_path).exists()


# ── One failing branch does not kill the others ───────────────────


@pytest.mark.asyncio
async def test_one_branch_fails_others_survive(tmp_path):
    settings = _make_settings(tmp_path, num_candidates=3, seed=42)
    image_gen = _SeedRecordingImageGen(fail_seeds=(43,))  # candidate 2
    pipeline = _make_pipeline(settings, image_gen=image_gen)

    result = await pipeline.generate(_default_input())

    candidates = result.metadata["candidates"]
    assert candidates[0]["error"] is None
    assert Path(candidates[0]["image_path"]).exists()
    assert "image gen exploded" in candidates[1]["error"]
    assert candidates[1]["image_path"] is None
    assert candidates[2]["error"] is None
    assert Path(candidates[2]["image_path"]).exists()

    # Primary stays candidate 1; root output exists
    assert result.metadata["primary_candidate"] == 1
    assert Path(result.image_path).exists()


@pytest.mark.asyncio
async def test_primary_falls_back_when_candidate_1_fails(tmp_path):
    settings = _make_settings(tmp_path, num_candidates=2, seed=42)
    image_gen = _SeedRecordingImageGen(fail_seeds=(42,))  # candidate 1
    pipeline = _make_pipeline(settings, image_gen=image_gen)

    result = await pipeline.generate(_default_input())

    assert result.metadata["primary_candidate"] == 2
    assert Path(result.image_path).exists()
    assert result.metadata["candidates"][0]["error"] is not None


# ── All branches failing raises ───────────────────────────────────


@pytest.mark.asyncio
async def test_all_branches_fail_raises(tmp_path):
    settings = _make_settings(tmp_path, num_candidates=2, seed=7)
    image_gen = _SeedRecordingImageGen(fail_seeds=(7, 8))
    pipeline = _make_pipeline(settings, image_gen=image_gen)

    with pytest.raises(RuntimeError, match="All 2 candidate branches failed"):
        await pipeline.generate(_default_input())


# ── Seed offsets are distinct per candidate ───────────────────────


@pytest.mark.asyncio
async def test_seed_offsets_distinct(tmp_path):
    settings = _make_settings(tmp_path, num_candidates=3, seed=100)
    image_gen = _SeedRecordingImageGen()
    pipeline = _make_pipeline(settings, image_gen=image_gen)

    result = await pipeline.generate(_default_input())

    assert sorted(image_gen.seeds) == [100, 101, 102]
    assert [c["seed"] for c in result.metadata["candidates"]] == [100, 101, 102]


@pytest.mark.asyncio
async def test_no_seed_means_no_offsets(tmp_path):
    settings = _make_settings(tmp_path, num_candidates=2)
    image_gen = _SeedRecordingImageGen()
    pipeline = _make_pipeline(settings, image_gen=image_gen)

    result = await pipeline.generate(_default_input())

    assert image_gen.seeds == [None, None]
    assert [c["seed"] for c in result.metadata["candidates"]] == [None, None]


# ── Progress events carry the candidate index ─────────────────────


@pytest.mark.asyncio
async def test_progress_events_include_candidate_index(tmp_path):
    settings = _make_settings(tmp_path, num_candidates=2)
    pipeline = _make_pipeline(settings)

    events = []

    def on_progress(event):
        events.append(event)

    await pipeline.generate(_default_input(), progress_callback=on_progress)

    from paperbanana_cn.core.types import PipelineProgressStage

    visualizer_starts = [e for e in events if e.stage == PipelineProgressStage.VISUALIZER_START]
    assert sorted((e.extra or {}).get("candidate") for e in visualizer_starts) == [1, 2]


# ── Budget guard aborts gracefully mid-fan-out ────────────────────


@pytest.mark.asyncio
async def test_budget_guard_stops_fanout_branches(tmp_path):
    """Once the shared tracker is over budget, every branch stops at its
    next between-iterations checkpoint instead of running to total_iters."""
    from paperbanana_cn.core.cost_tracker import CostTracker

    settings = _make_settings(
        tmp_path, num_candidates=2, refinement_iterations=3, budget_usd=0.0000001
    )
    tracker = CostTracker(budget=0.0000001)

    class _CostlyImageGen(_SeedRecordingImageGen):
        async def generate(self, *args, **kwargs):
            img = await super().generate(*args, **kwargs)
            # Simulate a paid image call against the shared tracker.
            tracker.record_image_call("openai_imagen", "gpt-image-1.5", agent="visualizer")
            return img

    revision = json.dumps(
        {
            "critic_suggestions": ["More contrast"],
            "revised_description": "Revised description",
        }
    )
    vlm = _MockVLM(responses=["Plan description", "Styled description", revision])
    pipeline = PaperBananaPipeline(
        settings=settings, vlm_client=vlm, image_gen_fn=_CostlyImageGen()
    )
    pipeline._cost_tracker = tracker

    result = await pipeline.generate(_default_input())

    # Critic always asks for revision, so without the budget guard each
    # branch would run 3 iterations; the shared tracker stops every branch
    # at its next checkpoint (candidate 2 may abort before its first image).
    candidates = result.metadata["candidates"]
    for cand in candidates:
        assert cand["error"] is None
        assert cand["iterations"] <= 1
        assert cand["budget_exceeded"] is True
    assert candidates[0]["iterations"] == 1
    assert result.metadata["cost"]["budget_exceeded"] is True
    assert Path(result.image_path).exists()


# ── Settings validation caps N at 8 ───────────────────────────────


def test_settings_rejects_invalid_num_candidates(tmp_path):
    with pytest.raises(ValueError):
        _make_settings(tmp_path, num_candidates=0)
    with pytest.raises(ValueError):
        _make_settings(tmp_path, num_candidates=9)


# ── CLI validation: 0 and >8 are rejected ─────────────────────────


def test_cli_rejects_out_of_range_num_candidates(tmp_path):
    from typer.testing import CliRunner

    from paperbanana_cn.cli import app

    runner = CliRunner()
    input_file = tmp_path / "method.txt"
    input_file.write_text("Sample methodology text.")

    for bad in ("0", "9"):
        result = runner.invoke(
            app,
            [
                "generate",
                "--input",
                str(input_file),
                "--caption",
                "test",
                "--num-candidates",
                bad,
                "--dry-run",
            ],
        )
        assert result.exit_code != 0
        # Strip ANSI escapes — rich colorizes CLI errors in CI, splitting
        # the flag name across style codes.
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "num-candidates" in plain
        assert "1<=x<=8" in plain


def test_cli_accepts_valid_num_candidates(tmp_path):
    from typer.testing import CliRunner

    from paperbanana_cn.cli import app

    runner = CliRunner()
    input_file = tmp_path / "method.txt"
    input_file.write_text("Sample methodology text.")

    result = runner.invoke(
        app,
        [
            "generate",
            "--input",
            str(input_file),
            "--caption",
            "test",
            "--num-candidates",
            "4",
            "--dry-run",
            "--legacy-connections",
        ],
    )
    assert result.exit_code == 0
