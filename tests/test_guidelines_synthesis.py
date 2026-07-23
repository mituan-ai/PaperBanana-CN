"""Tests for corpus-grounded style-guide synthesis."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from paperbanana.cli import app
from paperbanana.core.types import ReferenceExample
from paperbanana.guidelines.synthesis import (
    StyleGuideSynthesisError,
    sample_examples,
    synthesize_style_guide,
)

runner = CliRunner()


class RecordingVLM:
    """Mock VLM that records every generate() call."""

    name = "mock"
    model_name = "mock-model"
    cost_tracker = None

    def __init__(self, batch_response: str = "BATCH ANALYSIS", reduce_response: str = "# GUIDE"):
        self.calls: list[dict] = []
        self._batch_response = batch_response
        self._reduce_response = reduce_response

    async def generate(
        self,
        prompt,
        images=None,
        system_prompt=None,
        temperature=1.0,
        max_tokens=4096,
        response_format=None,
    ):
        self.calls.append({"prompt": prompt, "images": images})
        if images:
            return f"{self._batch_response} {len(self.calls)}"
        return self._reduce_response

    def is_available(self):
        return True


def _make_examples(tmp_path: Path, n: int, with_images: bool = True) -> list[ReferenceExample]:
    examples = []
    for i in range(n):
        image_path = tmp_path / f"ref_{i:03d}.png"
        if with_images:
            Image.new("RGB", (4, 4), color=(200, 220, 240)).save(image_path)
        examples.append(
            ReferenceExample(
                id=f"ref_{i:03d}",
                source_context=f"Context {i}",
                caption=f"Caption {i}",
                image_path=str(image_path),
                category="agents_llm" if i % 2 == 0 else "vision_perception",
            )
        )
    return examples


# ── Sampling ──────────────────────────────────────────────────────


def test_sampling_is_deterministic_with_seed(tmp_path):
    examples = _make_examples(tmp_path, 60)
    first = sample_examples(examples, sample_size=50, seed=42)
    second = sample_examples(examples, sample_size=50, seed=42)
    assert [e.id for e in first] == [e.id for e in second]
    assert len(first) == 50


def test_sampling_returns_all_when_corpus_small(tmp_path):
    examples = _make_examples(tmp_path, 10)
    sampled = sample_examples(examples, sample_size=50, seed=1)
    assert [e.id for e in sampled] == [e.id for e in examples]


def test_sampling_excludes_missing_images(tmp_path):
    examples = _make_examples(tmp_path, 5)
    missing = _make_examples(tmp_path / "nowhere", 3, with_images=False)
    sampled = sample_examples(examples + missing, sample_size=50, seed=1)
    assert len(sampled) == 5
    assert all(Path(e.image_path).exists() for e in sampled)


# ── Map-reduce synthesis ─────────────────────────────────────────


async def test_batching_math_and_reduce_output(tmp_path):
    """45 examples with batch_size 20 -> 3 map calls + 1 reduce call."""
    examples = _make_examples(tmp_path, 45)
    vlm = RecordingVLM(reduce_response="# Final Style Guide")

    result = await synthesize_style_guide(
        vlm,
        examples,
        guide_type="methodology",
        batch_size=20,
        sample_size=50,
        seed=7,
    )

    assert len(vlm.calls) == 4
    map_calls, reduce_call = vlm.calls[:3], vlm.calls[3]
    assert [len(c["images"]) for c in map_calls] == [20, 20, 5]
    assert reduce_call["images"] is None
    # The final output is the reduce result, not a map result.
    assert result == "# Final Style Guide\n"
    # The reduce prompt embeds every batch analysis.
    for i in range(1, 4):
        assert f"BATCH ANALYSIS {i}" in reduce_call["prompt"]
    assert "45" in reduce_call["prompt"]  # total figures


async def test_map_prompt_lists_figures_and_categories(tmp_path):
    examples = _make_examples(tmp_path, 3)
    vlm = RecordingVLM()

    await synthesize_style_guide(vlm, examples, guide_type="plot", batch_size=20)

    map_prompt = vlm.calls[0]["prompt"]
    assert "ref_000" in map_prompt
    assert "agents_llm" in map_prompt
    assert "statistical plots" in map_prompt
    assert "{figure_listing}" not in map_prompt  # placeholder substituted


async def test_sample_size_caps_figures_analyzed(tmp_path):
    examples = _make_examples(tmp_path, 30)
    vlm = RecordingVLM()

    await synthesize_style_guide(vlm, examples, batch_size=20, sample_size=10, seed=3)

    assert len(vlm.calls) == 2  # one map batch of 10 + one reduce
    assert len(vlm.calls[0]["images"]) == 10


async def test_no_examples_with_images_raises(tmp_path):
    missing = _make_examples(tmp_path / "nowhere", 3, with_images=False)
    vlm = RecordingVLM()

    with pytest.raises(StyleGuideSynthesisError, match="No reference examples"):
        await synthesize_style_guide(vlm, missing)
    assert vlm.calls == []


async def test_invalid_guide_type_raises(tmp_path):
    examples = _make_examples(tmp_path, 1)
    with pytest.raises(ValueError, match="guide_type"):
        await synthesize_style_guide(RecordingVLM(), examples, guide_type="poster")


async def test_progress_callback_invoked(tmp_path):
    examples = _make_examples(tmp_path, 3)
    messages: list[str] = []

    await synthesize_style_guide(
        RecordingVLM(),
        examples,
        batch_size=2,
        progress_callback=messages.append,
    )

    assert any("2 batch(es)" in m for m in messages)
    assert any("Batch 1/2" in m for m in messages)
    assert any("final style guide" in m for m in messages)


# ── CLI smoke tests (network-free) ───────────────────────────────


def test_cli_synthesize_rejects_invalid_type():
    result = runner.invoke(
        app,
        ["guidelines", "synthesize", "--type", "poster", "--output", "x.md"],
    )
    assert result.exit_code == 1
    assert "methodology" in result.output


def test_cli_synthesize_refuses_without_output_or_venue():
    result = runner.invoke(app, ["guidelines", "synthesize", "--type", "methodology"])
    assert result.exit_code == 1
    assert "--venue" in result.output
    assert "--output" in result.output


def test_cli_synthesize_rejects_venue_and_output_together(tmp_path):
    result = runner.invoke(
        app,
        [
            "guidelines",
            "synthesize",
            "--venue",
            "icml",
            "--output",
            str(tmp_path / "guide.md"),
        ],
    )
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


def test_cli_synthesize_rejects_unknown_venue():
    result = runner.invoke(app, ["guidelines", "synthesize", "--venue", "bogusconf"])
    assert result.exit_code == 1
    assert "neurips, icml, acl, or ieee" in result.output


def test_cli_synthesize_refuses_existing_output_without_force(tmp_path):
    existing = tmp_path / "guide.md"
    existing.write_text("existing guide")
    result = runner.invoke(
        app,
        [
            "guidelines",
            "synthesize",
            "--output",
            str(existing),
            "--legacy-connections",
        ],
    )
    assert result.exit_code == 1
    assert "already exists" in result.output
    assert existing.read_text() == "existing guide"


def test_cli_guidelines_help_lists_synthesize():
    result = runner.invoke(app, ["guidelines", "--help"], env={"NO_COLOR": "1", "TERM": "dumb"})
    assert result.exit_code == 0
    assert "synthesize" in result.output
