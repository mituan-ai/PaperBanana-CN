"""Tests for pipeline progress callback."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("PIL", reason="PIL/Pillow required for pipeline image mock")
from PIL import Image

from paperbanana_cn.core.config import Settings
from paperbanana_cn.core.pipeline import PaperBananaPipeline
from paperbanana_cn.core.types import (
    DiagramType,
    GenerationInput,
    PipelineProgressEvent,
    PipelineProgressStage,
)


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


@pytest.mark.asyncio
async def test_progress_callback_receives_events(tmp_path):
    """generate() invokes progress_callback with expected stages."""
    events: list[PipelineProgressEvent] = []

    def collect(event: PipelineProgressEvent) -> None:
        events.append(event)

    settings = Settings(
        output_dir=str(tmp_path / "outputs"),
        reference_set_path=str(tmp_path / "empty_refs"),
        refinement_iterations=2,
        save_iterations=False,
    )
    vlm = _MockVLM(
        responses=[
            "Initial plan description",
            "Styled final description",
            json.dumps({"critic_suggestions": [], "revised_description": None}),
        ]
    )
    image_gen = _MockImageGen()
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=image_gen)

    await pipeline.generate(
        GenerationInput(
            source_context="Minimal context",
            communicative_intent="Minimal caption",
            diagram_type=DiagramType.METHODOLOGY,
        ),
        progress_callback=collect,
    )

    stages = [e.stage for e in events]
    assert PipelineProgressStage.RETRIEVER_START in stages
    assert PipelineProgressStage.RETRIEVER_END in stages
    assert PipelineProgressStage.PLANNER_START in stages
    assert PipelineProgressStage.PLANNER_END in stages
    assert PipelineProgressStage.STYLIST_START in stages
    assert PipelineProgressStage.STYLIST_END in stages
    assert PipelineProgressStage.VISUALIZER_START in stages
    assert PipelineProgressStage.VISUALIZER_END in stages
    assert PipelineProgressStage.CRITIC_START in stages
    assert PipelineProgressStage.CRITIC_END in stages

    retriever_end = next(e for e in events if e.stage == PipelineProgressStage.RETRIEVER_END)
    assert retriever_end.seconds is not None
    assert retriever_end.seconds >= 0

    critic_ends = [e for e in events if e.stage == PipelineProgressStage.CRITIC_END]
    assert len(critic_ends) >= 1
    assert critic_ends[0].iteration is not None
    assert critic_ends[0].extra is not None
    assert "needs_revision" in critic_ends[0].extra


@pytest.mark.asyncio
async def test_progress_callback_with_optimize_receives_optimizer_events(tmp_path):
    """With optimize_inputs=True, callback receives optimizer start/end."""
    events: list[PipelineProgressEvent] = []

    def collect(event: PipelineProgressEvent) -> None:
        events.append(event)

    settings = Settings(
        output_dir=str(tmp_path / "outputs"),
        reference_set_path=str(tmp_path / "empty_refs"),
        refinement_iterations=1,
        save_iterations=False,
        optimize_inputs=True,
    )
    # Optimizer runs 2 parallel calls (context enricher + caption sharpener),
    # then planner, stylist, critic
    vlm = _MockVLM(
        responses=[
            "Enriched context",
            "Sharp caption",
            "Plan",
            "Styled",
            json.dumps({"critic_suggestions": [], "revised_description": None}),
        ]
    )
    image_gen = _MockImageGen()
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=image_gen)

    await pipeline.generate(
        GenerationInput(
            source_context="Context",
            communicative_intent="Caption",
            diagram_type=DiagramType.METHODOLOGY,
        ),
        progress_callback=collect,
    )

    stages = [e.stage for e in events]
    assert PipelineProgressStage.OPTIMIZER_START in stages
    assert PipelineProgressStage.OPTIMIZER_END in stages
    optimizer_end = next(e for e in events if e.stage == PipelineProgressStage.OPTIMIZER_END)
    assert optimizer_end.seconds is not None


@pytest.mark.asyncio
async def test_progress_callback_none_is_ignored(tmp_path):
    """Passing progress_callback=None runs without error."""
    settings = Settings(
        output_dir=str(tmp_path / "outputs"),
        reference_set_path=str(tmp_path / "empty_refs"),
        refinement_iterations=1,
        save_iterations=False,
    )
    vlm = _MockVLM(
        responses=[
            "Plan",
            "Styled",
            json.dumps({"critic_suggestions": [], "revised_description": None}),
        ]
    )
    image_gen = _MockImageGen()
    pipeline = PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=image_gen)

    result = await pipeline.generate(
        GenerationInput(
            source_context="Context",
            communicative_intent="Caption",
            diagram_type=DiagramType.METHODOLOGY,
        ),
        progress_callback=None,
    )
    assert result.image_path
    from pathlib import Path

    assert Path(result.image_path).exists()
