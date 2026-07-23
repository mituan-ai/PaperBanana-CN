"""Tests for refinement-loop rollback to the previous best image (issue #238)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("PIL", reason="PIL/Pillow required for pipeline image mock")
from pathlib import Path

from PIL import Image

from paperbanana_cn.core import pipeline as pipeline_mod
from paperbanana_cn.core.config import Settings
from paperbanana_cn.core.pipeline import PaperBananaPipeline
from paperbanana_cn.core.resume import ResumeState
from paperbanana_cn.core.types import (
    DiagramType,
    GenerationInput,
)

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


class _MockImageGen:
    name = "mock-image-gen"
    model_name = "mock-image-model"

    async def generate(self, *args, **kwargs):
        return Image.new("RGB", (128, 128), color=(255, 255, 255))


def _make_settings(tmp_path, **overrides):
    defaults = dict(
        output_dir=str(tmp_path / "outputs"),
        reference_set_path=str(tmp_path / "empty_refs"),
        refinement_iterations=3,
        save_iterations=False,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _default_input():
    return GenerationInput(
        source_context="Test methodology text",
        communicative_intent="Test caption",
        diagram_type=DiagramType.METHODOLOGY,
    )


_REVISION_CRITIQUE = json.dumps(
    {
        "critic_suggestions": ["Increase label font size"],
        "revised_description": "Revised description",
    }
)
_ACCEPT_CRITIQUE = json.dumps({"critic_suggestions": [], "revised_description": None})


def _fail_visualizer_at(pipeline, fail_iteration: int):
    """Patch the visualizer to raise on a specific iteration, delegating otherwise."""
    original_run = pipeline.visualizer.run

    async def flaky_visualizer(**kwargs):
        if kwargs.get("iteration") == fail_iteration:
            raise RuntimeError("image gen exploded")
        return await original_run(**kwargs)

    pipeline.visualizer.run = flaky_visualizer


# ── Fixture: fast retries (no waiting) ───────────────────────────


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


# ── Test: round-2 visualizer failure rolls back to iteration 1 ───


@pytest.mark.asyncio
async def test_visualizer_failure_round2_rolls_back_to_previous_image(tmp_path):
    """Iteration 2 visualizer failure keeps iteration 1's image as final output."""
    settings = _make_settings(tmp_path, save_iterations=True)
    # VLM responses: planner, stylist, critic iter 1 (requests revision)
    vlm = _MockVLM(
        responses=[
            "Plan description",
            "Styled description",
            _REVISION_CRITIQUE,
        ]
    )
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=_MockImageGen())
    _fail_visualizer_at(pipeline, fail_iteration=2)

    result = await pipeline.generate(_default_input())

    # Final output exists and comes from iteration 1
    assert result.image_path
    assert Path(result.image_path).exists()
    assert len(result.iterations) == 1
    assert result.iterations[0].iteration == 1

    # Metadata flags the rollback
    rollback = result.metadata["rollback"]
    assert rollback["rollback_occurred"] is True
    assert rollback["failed_iteration"] == 2
    assert rollback["rolled_back_to_iteration"] == 1
    assert rollback["stage"] == "visualizer"
    assert "image gen exploded" in rollback["error"]

    # Failure note is persisted alongside iteration artifacts
    run_dir = Path(settings.output_dir) / pipeline.run_id
    failure_note = json.loads((run_dir / "iter_2" / "failure.json").read_text())
    assert failure_note["failed"] is True
    assert failure_note["rolled_back_to_iteration"] == 1

    # Metadata on disk matches
    metadata = json.loads((run_dir / "metadata.json").read_text())
    assert metadata["rollback"]["rollback_occurred"] is True


# ── Test: round-1 visualizer failure still raises ────────────────


@pytest.mark.asyncio
async def test_visualizer_failure_round1_still_raises(tmp_path):
    """With no prior image, a first-round visualizer failure propagates."""
    settings = _make_settings(tmp_path)
    vlm = _MockVLM(responses=["Plan description", "Styled description"])
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=_MockImageGen())
    pipeline.visualizer.run = AsyncMock(side_effect=RuntimeError("image gen exploded"))

    with pytest.raises(RuntimeError, match="image gen exploded"):
        await pipeline.generate(_default_input())


# ── Test: no rollback metadata on a clean run ────────────────────


@pytest.mark.asyncio
async def test_no_rollback_metadata_on_clean_run(tmp_path):
    """A run without visualizer failures has no rollback section in metadata."""
    settings = _make_settings(tmp_path, refinement_iterations=1)
    vlm = _MockVLM(
        responses=[
            "Plan description",
            "Styled description",
            _ACCEPT_CRITIQUE,
        ]
    )
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=_MockImageGen())

    result = await pipeline.generate(_default_input())

    assert result.image_path
    assert "rollback" not in result.metadata


# ── Test: critic crash mid-loop keeps the current best image ─────


@pytest.mark.asyncio
async def test_critic_crash_mid_loop_keeps_best_image(tmp_path):
    """A critic exception in round 2 accepts round 2's image instead of failing."""
    settings = _make_settings(tmp_path)
    # VLM responses: planner, stylist (critic is patched below)
    vlm = _MockVLM(responses=["Plan description", "Styled description"])
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=_MockImageGen())

    from paperbanana_cn.core.types import CritiqueResult

    critic_calls = 0

    async def flaky_critic(**kwargs):
        nonlocal critic_calls
        critic_calls += 1
        if critic_calls == 1:
            return CritiqueResult(
                critic_suggestions=["Fix arrows"],
                revised_description="Revised description",
            )
        raise RuntimeError("critic exploded")

    pipeline.critic.run = flaky_critic

    result = await pipeline.generate(_default_input())

    # Run completed with both iterations; round 2's image is the final output
    assert result.image_path
    assert Path(result.image_path).exists()
    assert len(result.iterations) == 2
    assert not result.iterations[1].critique.needs_revision
    assert "rollback" not in result.metadata


# ── Test: continue_run rolls back to the previous run's image ────


@pytest.mark.asyncio
async def test_continue_run_rollback_keeps_previous_runs_image(tmp_path):
    """First continue iteration failing keeps the resumed run's last image."""
    settings = _make_settings(tmp_path)
    vlm = _MockVLM(responses=[])
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=_MockImageGen())

    # Simulate a previous run with an existing image
    run_dir = Path(settings.output_dir) / "run_prev"
    run_dir.mkdir(parents=True)
    prev_image = run_dir / "iteration_2.png"
    Image.new("RGB", (128, 128), color=(0, 0, 0)).save(prev_image)
    resume_state = ResumeState(
        run_dir=str(run_dir),
        run_id="run_prev",
        source_context="Test methodology text",
        communicative_intent="Test caption",
        diagram_type=DiagramType.METHODOLOGY,
        last_description="Previous description",
        last_iteration=2,
        last_image_path=str(prev_image),
    )

    pipeline.visualizer.run = AsyncMock(side_effect=RuntimeError("image gen exploded"))

    result = await pipeline.continue_run(resume_state, additional_iterations=2)

    # Final output exists and was rebuilt from the previous run's image
    assert result.image_path
    assert Path(result.image_path).exists()
    assert len(result.iterations) == 0

    rollback = result.metadata["rollback"]
    assert rollback["rollback_occurred"] is True
    assert rollback["failed_iteration"] == 3
    assert rollback["rolled_back_to_iteration"] == 2

    metadata = json.loads((run_dir / "metadata_continued.json").read_text())
    assert metadata["rollback"]["rollback_occurred"] is True
