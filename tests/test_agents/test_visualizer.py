"""Tests for VisualizerAgent code extraction edge cases and vector export."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperbanana.agents.visualizer import VisualizerAgent
from paperbanana.core.config import OUTPUT_RESOLUTION_VALUES
from paperbanana.core.types import ASPECT_RATIO_VALUES


class _DummyImageGen:
    async def generate(self, *args, **kwargs):
        return None


class _DummyVLM:
    async def generate(self, *args, **kwargs):
        return ""


def _make_agent(tmp_path):
    return VisualizerAgent(
        image_gen=_DummyImageGen(),
        vlm_provider=_DummyVLM(),
        prompt_dir=str(tmp_path),
        output_dir=str(tmp_path),
    )


def test_extract_code_handles_truncated_python_block(tmp_path):
    agent = _make_agent(tmp_path)
    response = "```python\nimport matplotlib.pyplot as plt\nplt.figure()\n"
    code = agent._extract_code(response)
    assert code == "import matplotlib.pyplot as plt\nplt.figure()"


def test_extract_code_handles_truncated_generic_block(tmp_path):
    agent = _make_agent(tmp_path)
    response = "```\nprint('hello')\n"
    code = agent._extract_code(response)
    assert code == "print('hello')"


def test_extract_code_handles_complete_python_block(tmp_path):
    agent = _make_agent(tmp_path)
    response = "```python\nprint('ok')\n```\nextra"
    code = agent._extract_code(response)
    assert code == "print('ok')"


def test_extract_code_handles_plain_code_response(tmp_path):
    agent = _make_agent(tmp_path)
    response = "import matplotlib.pyplot as plt\nplt.figure()"
    code = agent._extract_code(response)
    assert code == response


# ── Vector export tests ───────────────────────────────────────────────────────

_SIMPLE_PLOT_CODE = """\
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
plt.savefig(OUTPUT_PATH, bbox_inches='tight')
"""


def test_execute_plot_code_produces_raster_only_by_default(tmp_path):
    agent = _make_agent(tmp_path)
    output_path = str(tmp_path / "plot.png")
    success = agent._execute_plot_code(_SIMPLE_PLOT_CODE, output_path)
    assert success
    assert Path(output_path).exists()
    assert agent._last_vector_paths == {}


def test_execute_plot_code_produces_svg_and_pdf_when_requested(tmp_path):
    agent = _make_agent(tmp_path)
    output_path = str(tmp_path / "plot.png")
    success = agent._execute_plot_code(
        _SIMPLE_PLOT_CODE, output_path, vector_formats=["svg", "pdf"]
    )
    assert success
    assert Path(output_path).exists()
    assert "svg" in agent._last_vector_paths
    assert "pdf" in agent._last_vector_paths
    assert Path(agent._last_vector_paths["svg"]).exists()
    assert Path(agent._last_vector_paths["pdf"]).exists()


def test_execute_plot_code_svg_path_has_correct_suffix(tmp_path):
    agent = _make_agent(tmp_path)
    output_path = str(tmp_path / "my_plot.png")
    agent._execute_plot_code(_SIMPLE_PLOT_CODE, output_path, vector_formats=["svg"])
    assert agent._last_vector_paths["svg"] == str(tmp_path / "my_plot.svg")


def test_execute_plot_code_strips_vlm_vector_path_assignments(tmp_path):
    """VLM-injected VECTOR_PATH_* assignments must be overridden by our header."""
    agent = _make_agent(tmp_path)
    output_path = str(tmp_path / "plot.png")
    code_with_stale_path = 'VECTOR_PATH_SVG = "/stale/path.svg"\n' + _SIMPLE_PLOT_CODE
    success = agent._execute_plot_code(code_with_stale_path, output_path, vector_formats=["svg"])
    assert success
    # Our injected path, not the stale one, should be used
    assert agent._last_vector_paths.get("svg") == str(tmp_path / "plot.svg")


def test_execute_plot_code_sets_empty_vector_paths_on_failure(tmp_path):
    agent = _make_agent(tmp_path)
    output_path = str(tmp_path / "plot.png")
    bad_code = "raise RuntimeError('intentional failure')"
    success = agent._execute_plot_code(bad_code, output_path, vector_formats=["svg", "pdf"])
    assert not success
    assert agent._last_vector_paths == {}


def test_last_vector_paths_reset_on_each_run_call(tmp_path):
    """_last_vector_paths from a previous run must not bleed into the next."""
    agent = _make_agent(tmp_path)
    output_path = str(tmp_path / "plot.png")
    # First call with vector export
    agent._execute_plot_code(_SIMPLE_PLOT_CODE, output_path, vector_formats=["svg"])
    assert "svg" in agent._last_vector_paths
    # Second call without vector export
    output_path2 = str(tmp_path / "plot2.png")
    agent._execute_plot_code(_SIMPLE_PLOT_CODE, output_path2)
    assert agent._last_vector_paths == {}


def test_ratio_to_dimensions_supports_high_resolution_landscape():
    assert VisualizerAgent._ratio_to_dimensions("16:9", output_resolution="4k") == (3840, 2160)


def test_ratio_to_dimensions_supports_2k_landscape():
    assert VisualizerAgent._ratio_to_dimensions("16:9", output_resolution="2k") == (2048, 1152)


@pytest.mark.parametrize(
    ("ratio", "resolution", "expected"),
    [
        ("5:4", "1k", (1024, 816)),
        ("4:5", "1k", (816, 1024)),
        ("5:4", "2k", (2048, 1632)),
        ("4:5", "4k", (3072, 3840)),
    ],
)
def test_ratio_to_dimensions_supports_cn_ratios(ratio, resolution, expected):
    assert VisualizerAgent._ratio_to_dimensions(ratio, resolution) == expected


@pytest.mark.parametrize("ratio", ASPECT_RATIO_VALUES)
@pytest.mark.parametrize("resolution", OUTPUT_RESOLUTION_VALUES)
def test_ratio_resolution_matrix_uses_single_dimension_converter(ratio, resolution):
    width, height = VisualizerAgent._ratio_to_dimensions(ratio, resolution)
    expected_long_edge = {"1k": 1024, "2k": 2048, "4k": 3840}[resolution]
    ratio_width, ratio_height = (int(part) for part in ratio.split(":"))

    assert max(width, height) == expected_long_edge
    assert width % 16 == 0
    assert height % 16 == 0
    actual_ratio = width / height
    target_ratio = ratio_width / ratio_height
    assert abs((actual_ratio / target_ratio) - 1) < 0.02


def test_ratio_to_dimensions_rejects_unknown_ratio():
    with pytest.raises(ValueError, match="Unsupported aspect ratio"):
        VisualizerAgent._ratio_to_dimensions("16:10")


# ── Sketch-guided prompt note ─────────────────────────────────────────────────


class _CapturingImageGen:
    def __init__(self):
        self.captured = {}

    async def generate(self, prompt, **kwargs):
        from PIL import Image

        self.captured["prompt"] = prompt
        return Image.new("RGB", (8, 8), color=(255, 255, 255))


async def test_generate_diagram_notes_user_sketch_when_guided(tmp_path):
    """sketch_guided=True adds a one-line mention to the diagram prompt."""
    from paperbanana.core.utils import find_prompt_dir

    gen = _CapturingImageGen()
    agent = VisualizerAgent(
        image_gen=gen,
        vlm_provider=_DummyVLM(),
        prompt_dir=find_prompt_dir(),
        output_dir=str(tmp_path),
    )

    await agent.run(description="a diagram description", sketch_guided=True)
    assert "user-provided reference sketch" in gen.captured["prompt"]

    await agent.run(description="a diagram description")
    assert "user-provided reference sketch" not in gen.captured["prompt"]
