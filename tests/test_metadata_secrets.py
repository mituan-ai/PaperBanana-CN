"""Tests for preventing API secrets from being written to run metadata."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from paperbanana.core.config import Settings
from paperbanana.core.pipeline import PaperBananaPipeline
from paperbanana.core.types import GenerationInput


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
        return Image.new("RGB", (128, 128), color=(200, 200, 200))


def _critic_satisfied() -> str:
    return json.dumps({"critic_suggestions": [], "revised_description": None})


@pytest.mark.asyncio
async def test_api_keys_are_excluded_from_metadata_config_snapshot(tmp_path):
    settings = Settings(
        output_dir=str(tmp_path / "outputs"),
        reference_set_path=str(tmp_path / "refs"),
        refinement_iterations=1,
        save_iterations=True,
        vlm_api_key="profile-vlm-secret",
        image_api_key="profile-image-secret",
        google_api_key="google-secret",
        openai_api_key="openai-secret",
        openrouter_api_key="openrouter-secret",
        anthropic_api_key="anthropic-secret",
        atlascloud_api_key="atlas-secret",
        litellm_api_key="litellm-secret",
    )
    vlm = _MockVLM(["Plan", "Style", _critic_satisfied()])
    pipeline = PaperBananaPipeline(
        settings=settings,
        vlm_client=vlm,
        image_gen_fn=_MockImageGen(),
    )

    result = await pipeline.generate(
        GenerationInput(source_context="ctx", communicative_intent="intent")
    )

    config_snapshot = result.metadata["config_snapshot"]
    for key in (
        "vlm_api_key",
        "image_api_key",
        "google_api_key",
        "openai_api_key",
        "openrouter_api_key",
        "anthropic_api_key",
        "atlascloud_api_key",
        "litellm_api_key",
    ):
        assert key not in config_snapshot

    metadata_path = Path(settings.output_dir) / result.metadata["run_id"] / "metadata.json"
    saved = json.loads(metadata_path.read_text(encoding="utf-8"))
    saved_config_snapshot = saved["config_snapshot"]
    for key in (
        "vlm_api_key",
        "image_api_key",
        "google_api_key",
        "openai_api_key",
        "openrouter_api_key",
        "anthropic_api_key",
        "atlascloud_api_key",
        "litellm_api_key",
    ):
        assert key not in saved_config_snapshot

    serialized_metadata = metadata_path.read_text(encoding="utf-8")
    for secret in (
        "profile-vlm-secret",
        "profile-image-secret",
        "anthropic-secret",
        "atlas-secret",
        "litellm-secret",
    ):
        assert secret not in serialized_metadata
