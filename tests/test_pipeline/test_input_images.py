"""Pipeline wiring tests for user-provided reference/sketch images."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from paperbanana_cn.core.config import Settings
from paperbanana_cn.core.pipeline import PaperBananaPipeline
from paperbanana_cn.core.types import CritiqueResult, DiagramType, GenerationInput


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


def _make_sketch(tmp_path) -> str:
    sketch = tmp_path / "sketch.png"
    Image.new("RGB", (4, 4), color=(0, 0, 255)).save(sketch)
    return str(sketch)


def _make_pipeline(tmp_path) -> PaperBananaPipeline:
    settings = Settings(
        output_dir=str(tmp_path / "outputs"),
        reference_set_path=str(tmp_path / "empty_refs"),
        refinement_iterations=1,
    )
    vlm = _MockVLM(
        responses=[
            "planner description",
            "styled description",
            json.dumps({"critic_suggestions": [], "revised_description": None}),
        ]
    )
    return PaperBananaPipeline(settings=settings, vlm_client=vlm, image_gen_fn=_MockImageGen())


@pytest.mark.asyncio
async def test_planner_receives_input_images_and_critic_does_not(tmp_path):
    """The sketch reaches the Planner; the Critic judges against source text only."""
    sketch_path = _make_sketch(tmp_path)
    pipeline = _make_pipeline(tmp_path)

    pipeline.retriever.run = AsyncMock(return_value=[])
    pipeline.planner.run = AsyncMock(return_value=("planner description", None))
    pipeline.critic.run = AsyncMock(return_value=CritiqueResult())

    await pipeline.generate(
        GenerationInput(
            source_context="source context",
            communicative_intent="caption",
            diagram_type=DiagramType.METHODOLOGY,
            input_images=[sketch_path],
        )
    )

    # Planner got the sketch paths.
    planner_kwargs = pipeline.planner.run.await_args.kwargs
    assert planner_kwargs["input_images"] == [sketch_path]

    # Critic was called, but never with the sketch (no image/path argument
    # other than the generated image; no mention of the sketch path at all).
    pipeline.critic.run.assert_awaited()
    critic_kwargs = pipeline.critic.run.await_args.kwargs
    assert "input_images" not in critic_kwargs
    assert "images" not in critic_kwargs
    for value in critic_kwargs.values():
        if isinstance(value, str):
            assert sketch_path not in value
        elif isinstance(value, (list, tuple)):
            assert sketch_path not in value


@pytest.mark.asyncio
async def test_run_input_json_records_input_images(tmp_path):
    """run_input.json persists input_images for reproducibility."""
    sketch_path = _make_sketch(tmp_path)
    pipeline = _make_pipeline(tmp_path)
    pipeline.retriever.run = AsyncMock(return_value=[])
    pipeline.planner.run = AsyncMock(return_value=("planner description", None))
    pipeline.critic.run = AsyncMock(return_value=CritiqueResult())

    await pipeline.generate(
        GenerationInput(
            source_context="source context",
            communicative_intent="caption",
            diagram_type=DiagramType.METHODOLOGY,
            input_images=[sketch_path],
        )
    )

    run_input = json.loads((pipeline._run_dir / "run_input.json").read_text(encoding="utf-8"))
    assert run_input["input_images"] == [sketch_path]
