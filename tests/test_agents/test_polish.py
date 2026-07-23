"""Tests for PolishAgent: suggestion parsing, suggest/apply flow, guided-edit gating."""

from __future__ import annotations

import pytest
from PIL import Image

from paperbanana.agents.polish import MAX_SUGGESTIONS, PolishAgent


class _FakeVLM:
    """VLM stub that records calls and returns a canned response."""

    def __init__(self, response: str):
        self.response = response
        self.calls: list[dict] = []

    async def generate(self, prompt, images=None, **kwargs):
        self.calls.append({"prompt": prompt, "images": images, **kwargs})
        return self.response


class _FakeEditImageGen:
    """Image gen stub that supports guided edits (declares an images kwarg)."""

    name = "fake_edit"
    model_name = "fake-edit-model"
    supports_image_edit = True

    def __init__(self):
        self.calls: list[dict] = []

    async def generate(
        self,
        prompt,
        negative_prompt=None,
        width=1024,
        height=1024,
        seed=None,
        aspect_ratio=None,
        quality=None,
        images=None,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "images": images,
                "width": width,
                "height": height,
                "seed": seed,
                "aspect_ratio": aspect_ratio,
            }
        )
        return Image.new("RGB", (64, 48), color=(240, 240, 240))


class _TextOnlyImageGen:
    """Image gen stub matching the base text-to-image contract (no images kwarg)."""

    name = "text_only"
    model_name = "text-only-model"
    supports_image_edit = False

    async def generate(
        self,
        prompt,
        negative_prompt=None,
        width=1024,
        height=1024,
        seed=None,
        aspect_ratio=None,
        quality=None,
    ):
        return Image.new("RGB", (8, 8))


@pytest.fixture
def prompt_dir(tmp_path):
    polish_dir = tmp_path / "prompts" / "polish"
    polish_dir.mkdir(parents=True)
    (polish_dir / "suggest.txt").write_text(
        "STYLE GUIDE:\n{style_guide}\nMax: {max_suggestions}", encoding="utf-8"
    )
    (polish_dir / "apply.txt").write_text(
        "Apply these improvements:\n{suggestions}", encoding="utf-8"
    )
    return str(tmp_path / "prompts")


@pytest.fixture
def figure(tmp_path):
    path = tmp_path / "figure.png"
    Image.new("RGB", (64, 48), color=(255, 255, 255)).save(path)
    return path


def _make_agent(prompt_dir, tmp_path, vlm_response="NO_SUGGESTIONS", image_gen=None):
    return PolishAgent(
        image_gen=image_gen if image_gen is not None else _FakeEditImageGen(),
        vlm_provider=_FakeVLM(vlm_response),
        prompt_dir=prompt_dir,
        output_dir=str(tmp_path / "out"),
    )


# ── Suggestion parsing ────────────────────────────────────────────────────────


def test_parse_suggestions_numbered_list():
    response = "1. Use pastel fills for module backgrounds\n2) Align arrows to a grid"
    assert PolishAgent._parse_suggestions(response) == [
        "Use pastel fills for module backgrounds",
        "Align arrows to a grid",
    ]


def test_parse_suggestions_bulleted_list():
    response = "- Soften the box corners\n* Use sans-serif labels\n• Reserve red for the loss"
    assert PolishAgent._parse_suggestions(response) == [
        "Soften the box corners",
        "Use sans-serif labels",
        "Reserve red for the loss",
    ]


def test_parse_suggestions_fenced_output():
    response = "```\n1. Use a single accent color\n2. Increase label font size\n```"
    assert PolishAgent._parse_suggestions(response) == [
        "Use a single accent color",
        "Increase label font size",
    ]


def test_parse_suggestions_ignores_preamble_prose():
    response = "Here are my suggestions for the figure:\n1. Use thinner arrows"
    assert PolishAgent._parse_suggestions(response) == ["Use thinner arrows"]


def test_parse_suggestions_strips_bold_markers():
    response = "1. **Colors**: replace saturated red with pale blue"
    assert PolishAgent._parse_suggestions(response) == [
        "Colors: replace saturated red with pale blue"
    ]


def test_parse_suggestions_no_suggestions_sentinel():
    assert PolishAgent._parse_suggestions("NO_SUGGESTIONS") == []


def test_parse_suggestions_empty_and_none():
    assert PolishAgent._parse_suggestions("") == []
    assert PolishAgent._parse_suggestions(None) == []


def test_parse_suggestions_caps_at_max():
    response = "\n".join(f"{i}. Suggestion {i}" for i in range(1, 15))
    parsed = PolishAgent._parse_suggestions(response)
    assert len(parsed) == MAX_SUGGESTIONS
    assert parsed[0] == "Suggestion 1"
    assert parsed[-1] == f"Suggestion {MAX_SUGGESTIONS}"


def test_parse_suggestions_unparseable_prose_returns_empty():
    assert PolishAgent._parse_suggestions("The figure looks somewhat busy overall.") == []


# ── Suggest step ──────────────────────────────────────────────────────────────


async def test_suggest_sends_image_and_style_guide_to_vlm(prompt_dir, tmp_path):
    agent = _make_agent(prompt_dir, tmp_path, vlm_response="1. Use pastel fills")
    image = Image.new("RGB", (32, 32))

    suggestions = await agent.suggest(image, style_guide="Pastel palettes only")

    assert suggestions == ["Use pastel fills"]
    call = agent.vlm.calls[0]
    assert call["images"] == [image]
    assert "Pastel palettes only" in call["prompt"]
    assert str(MAX_SUGGESTIONS) in call["prompt"]


# ── Apply step ────────────────────────────────────────────────────────────────


async def test_apply_sends_original_image_and_suggestions_to_image_gen(prompt_dir, tmp_path):
    image_gen = _FakeEditImageGen()
    agent = _make_agent(prompt_dir, tmp_path, image_gen=image_gen)
    image = Image.new("RGB", (64, 48))
    output_path = str(tmp_path / "out" / "polished.png")

    result = await agent.apply(
        image,
        ["Use pastel fills", "Align arrows"],
        output_path=output_path,
        aspect_ratio="16:9",
        seed=7,
    )

    assert result == output_path
    call = image_gen.calls[0]
    # The original figure is the edit base
    assert call["images"] == [image]
    # Numbered suggestions are embedded in the edit prompt
    assert "1. Use pastel fills" in call["prompt"]
    assert "2. Align arrows" in call["prompt"]
    assert call["aspect_ratio"] == "16:9"
    assert call["seed"] == 7
    # Dimensions default to the input figure's size
    assert (call["width"], call["height"]) == (64, 48)
    # Polished image is saved to disk
    from pathlib import Path

    assert Path(output_path).exists()


async def test_apply_rejects_provider_without_guided_edit_support(prompt_dir, tmp_path):
    agent = _make_agent(prompt_dir, tmp_path, image_gen=_TextOnlyImageGen())

    with pytest.raises(RuntimeError, match="guided image editing"):
        await agent.apply(Image.new("RGB", (8, 8)), ["x"], output_path=str(tmp_path / "p.png"))


def test_supports_guided_edit_detection():
    assert PolishAgent.supports_guided_edit(_FakeEditImageGen())
    assert not PolishAgent.supports_guided_edit(_TextOnlyImageGen())


def test_google_imagen_supports_guided_edit():
    from paperbanana.providers.image_gen.google_imagen import GoogleImagenGen

    assert PolishAgent.supports_guided_edit(GoogleImagenGen(api_key="test"))


# ── Run orchestration ─────────────────────────────────────────────────────────


async def test_run_suggests_then_applies(prompt_dir, tmp_path, figure):
    image_gen = _FakeEditImageGen()
    agent = _make_agent(
        prompt_dir, tmp_path, vlm_response="1. Use pastel fills", image_gen=image_gen
    )

    result_path, suggestions = await agent.run(str(figure), style_guide="guide")

    assert suggestions == ["Use pastel fills"]
    assert result_path == str(tmp_path / "out" / "polished_iter_1.png")
    assert len(image_gen.calls) == 1


async def test_run_skips_apply_when_no_suggestions(prompt_dir, tmp_path, figure):
    image_gen = _FakeEditImageGen()
    agent = _make_agent(prompt_dir, tmp_path, vlm_response="NO_SUGGESTIONS", image_gen=image_gen)

    result_path, suggestions = await agent.run(str(figure), style_guide="guide")

    assert suggestions == []
    assert result_path == str(figure)
    assert image_gen.calls == []


def test_missing_prompt_template_raises(tmp_path):
    agent = PolishAgent(
        image_gen=_FakeEditImageGen(),
        vlm_provider=_FakeVLM(""),
        prompt_dir=str(tmp_path),
    )
    with pytest.raises(FileNotFoundError):
        agent._load_polish_prompt("suggest")
