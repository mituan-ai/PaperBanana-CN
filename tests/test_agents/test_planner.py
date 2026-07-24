"""Tests for planner agent formatting behavior."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from paperbanana_cn.agents.planner import PlannerAgent
from paperbanana_cn.core.types import ReferenceExample
from paperbanana_cn.core.utils import find_prompt_dir


class _MockVLM:
    name = "mock-vlm"
    model_name = "mock-model"

    async def generate(self, *args, **kwargs):
        return "ok"


class _CapturingVLM:
    """Mock VLM that records the prompt and image parts it receives."""

    name = "mock-vlm"
    model_name = "mock-model"

    def __init__(self):
        self.captured: dict = {}

    async def generate(self, prompt, images=None, **kwargs):
        self.captured["prompt"] = prompt
        self.captured["images"] = images
        return "a detailed description\nRECOMMENDED_RATIO: 16:9"


def test_format_examples_includes_structure_hints():
    agent = PlannerAgent(_MockVLM())
    text = agent._format_examples(
        [
            ReferenceExample(
                id="ref_001",
                source_context="context",
                caption="caption",
                image_path="",
                structure_hints={"nodes": ["A"], "edges": ["A->B"]},
            )
        ]
    )

    assert "Structure Hints" in text
    assert "nodes" in text


def test_has_valid_image_accepts_safe_https_url():
    """_has_valid_image accepts safe https URLs."""
    agent = PlannerAgent(_MockVLM())
    ex = ReferenceExample(
        id="x",
        source_context="",
        caption="",
        image_path="https://example.com/diagram.png",
    )
    assert agent._has_valid_image(ex) is True


def test_has_valid_image_rejects_insecure_or_local_urls():
    """_has_valid_image rejects insecure schemes and localhost/private targets."""
    agent = PlannerAgent(_MockVLM())
    insecure = ReferenceExample(
        id="x",
        source_context="",
        caption="",
        image_path="http://example.com/fig.png",
    )
    localhost = ReferenceExample(
        id="x",
        source_context="",
        caption="",
        image_path="https://localhost/fig.png",
    )
    private_ip = ReferenceExample(
        id="x",
        source_context="",
        caption="",
        image_path="https://10.0.0.12/fig.png",
    )
    assert agent._has_valid_image(insecure) is False
    assert agent._has_valid_image(localhost) is False
    assert agent._has_valid_image(private_ip) is False


async def test_planner_attaches_user_sketch_images_after_exemplars(tmp_path):
    """User sketch images are attached after exemplar images and labeled in the prompt."""
    ref_img = tmp_path / "ref.png"
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(ref_img)
    sketch = tmp_path / "sketch.png"
    Image.new("RGB", (4, 4), color=(0, 0, 255)).save(sketch)

    vlm = _CapturingVLM()
    agent = PlannerAgent(vlm, prompt_dir=find_prompt_dir())

    description, ratio = await agent.run(
        source_context="methodology text",
        caption="figure caption",
        examples=[
            ReferenceExample(
                id="ref_001",
                source_context="ctx",
                caption="cap",
                image_path=str(ref_img),
            )
        ],
        input_images=[str(sketch)],
    )

    assert description == "a detailed description"
    assert ratio == "16:9"
    # Exemplar image first, user sketch attached last.
    images = vlm.captured["images"]
    assert len(images) == 2
    assert images[0].size == (2, 2)
    assert images[-1].size == (4, 4)
    # The prompt labels the trailing image parts as user-provided.
    assert "User-Provided Reference/Sketch" in vlm.captured["prompt"]


@pytest.mark.parametrize("ratio", ["4:5", "5:4"])
def test_planner_accepts_all_shared_aspect_ratios(ratio):
    description, parsed = PlannerAgent._parse_ratio(
        f"a detailed description\nRECOMMENDED_RATIO: {ratio}"
    )
    assert description == "a detailed description"
    assert parsed == ratio


async def test_planner_without_user_images_keeps_prompt_unchanged(tmp_path):
    """No sketch label or extra image parts appear when input_images is absent."""
    ref_img = tmp_path / "ref.png"
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(ref_img)

    vlm = _CapturingVLM()
    agent = PlannerAgent(vlm, prompt_dir=find_prompt_dir())

    await agent.run(
        source_context="methodology text",
        caption="figure caption",
        examples=[
            ReferenceExample(
                id="ref_001",
                source_context="ctx",
                caption="cap",
                image_path=str(ref_img),
            )
        ],
    )

    assert len(vlm.captured["images"]) == 1
    assert "User-Provided Reference/Sketch" not in vlm.captured["prompt"]


def test_load_example_images_loads_from_url(monkeypatch):
    """_load_example_images fetches and loads images from http(s) URLs."""
    agent = PlannerAgent(_MockVLM())
    # 1x1 red PNG bytes
    buf = BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="PNG")
    image = Image.open(BytesIO(buf.getvalue())).convert("RGB")
    monkeypatch.setattr(agent, "_fetch_remote_image", lambda _url: image)
    examples = [
        ReferenceExample(
            id="ext_1",
            source_context="ctx",
            caption="cap",
            image_path="https://example.com/ref.png",
        )
    ]
    images = agent._load_example_images(examples)
    assert len(images) == 1
    assert images[0].size == (1, 1)
