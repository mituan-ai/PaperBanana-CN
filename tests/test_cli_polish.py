"""Tests for the `paperbanana polish` CLI command (network-free)."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from paperbanana.cli import app
from paperbanana.providers.registry import ProviderRegistry

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """rich colorizes output in CI; strip ANSI escapes before asserting."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _write_figure(path: Path) -> None:
    Image.new("RGB", (64, 48), color=(255, 255, 255)).save(path)


class _FakeVLM:
    name = "fake_vlm"
    model_name = "fake-vlm"
    cost_tracker = None

    def __init__(self, response: str = "1. Use pastel module fills\n2. Align arrows to a grid"):
        self.response = response
        self.calls = 0

    async def generate(self, prompt, images=None, **kwargs):
        self.calls += 1
        return self.response


class _FakeEditImageGen:
    name = "fake_edit"
    model_name = "fake-edit"
    cost_tracker = None
    supports_image_edit = True

    def __init__(self):
        self.calls: list[dict] = []

    async def generate(self, prompt, images=None, **kwargs):
        self.calls.append({"prompt": prompt, "images": images})
        return Image.new("RGB", (64, 48), color=(240, 240, 240))


class _TextOnlyImageGen:
    name = "text_only"
    model_name = "text-only"
    cost_tracker = None
    supports_image_edit = False

    async def generate(self, prompt, negative_prompt=None, width=1024, height=1024):
        return Image.new("RGB", (8, 8))


def _patch_providers(monkeypatch, vlm, image_gen):
    monkeypatch.setattr(ProviderRegistry, "create_vlm", lambda settings: vlm)
    monkeypatch.setattr(ProviderRegistry, "create_image_gen", lambda settings: image_gen)


def test_polish_rejects_missing_input_file():
    result = runner.invoke(app, ["polish", "--input", "/nonexistent/figure.png"])
    assert result.exit_code == 1
    assert "not found" in _strip_ansi(result.output)


def test_polish_rejects_non_image_input(tmp_path):
    bogus = tmp_path / "figure.png"
    bogus.write_text("this is not an image", encoding="utf-8")

    result = runner.invoke(app, ["polish", "--input", str(bogus)])
    assert result.exit_code == 1
    assert "not a readable image" in _strip_ansi(result.output)


def test_polish_rejects_bad_venue(tmp_path):
    figure = tmp_path / "figure.png"
    _write_figure(figure)

    result = runner.invoke(app, ["polish", "--input", str(figure), "--venue", "siggraph"])
    assert result.exit_code == 1
    assert "--venue must be" in _strip_ansi(result.output)


def test_polish_rejects_text_only_image_provider(tmp_path, monkeypatch):
    figure = tmp_path / "figure.png"
    _write_figure(figure)
    _patch_providers(monkeypatch, _FakeVLM(), _TextOnlyImageGen())

    result = runner.invoke(app, ["polish", "--input", str(figure), "--legacy-connections"])
    assert result.exit_code == 1
    assert "does not support guided image editing" in _strip_ansi(result.output)


def test_polish_single_round_prints_suggestions_and_saves_output(tmp_path, monkeypatch):
    figure = tmp_path / "figure.png"
    _write_figure(figure)
    output = tmp_path / "out" / "final.png"
    vlm = _FakeVLM()
    image_gen = _FakeEditImageGen()
    _patch_providers(monkeypatch, vlm, image_gen)

    result = runner.invoke(
        app,
        [
            "polish",
            "--input",
            str(figure),
            "--output",
            str(output),
            "--legacy-connections",
        ],
    )

    out = _strip_ansi(result.output)
    assert result.exit_code == 0, out
    # Suggestions are printed to the console so users see what changed
    assert "Use pastel module fills" in out
    assert "Align arrows to a grid" in out
    assert "Done!" in out
    assert output.exists()
    # One suggest call, one apply call
    assert vlm.calls == 1
    assert len(image_gen.calls) == 1
    # The apply step received the original figure as the edit base
    assert len(image_gen.calls[0]["images"]) == 1
    assert "1. Use pastel module fills" in image_gen.calls[0]["prompt"]


def test_polish_iterations_repeat_suggest_apply(tmp_path, monkeypatch):
    figure = tmp_path / "figure.png"
    _write_figure(figure)
    output = tmp_path / "out" / "final.png"
    vlm = _FakeVLM()
    image_gen = _FakeEditImageGen()
    _patch_providers(monkeypatch, vlm, image_gen)

    result = runner.invoke(
        app,
        [
            "polish",
            "--input",
            str(figure),
            "--output",
            str(output),
            "--iterations",
            "3",
            "--legacy-connections",
        ],
    )

    assert result.exit_code == 0, _strip_ansi(result.output)
    assert vlm.calls == 3
    assert len(image_gen.calls) == 3
    assert output.exists()
    # Intermediate round outputs land next to the final output
    assert (tmp_path / "out" / "polished_iter_1.png").exists()
    assert (tmp_path / "out" / "polished_iter_3.png").exists()


def test_polish_stops_when_no_more_suggestions(tmp_path, monkeypatch):
    figure = tmp_path / "figure.png"
    _write_figure(figure)
    output = tmp_path / "out" / "final.png"
    vlm = _FakeVLM(response="NO_SUGGESTIONS")
    image_gen = _FakeEditImageGen()
    _patch_providers(monkeypatch, vlm, image_gen)

    result = runner.invoke(
        app,
        [
            "polish",
            "--input",
            str(figure),
            "--output",
            str(output),
            "--iterations",
            "5",
            "--legacy-connections",
        ],
    )

    out = _strip_ansi(result.output)
    assert result.exit_code == 0, out
    # Suggest ran once, found nothing, and the loop stopped without editing
    assert vlm.calls == 1
    assert image_gen.calls == []
    assert "already" in out
    assert not output.exists()


def test_polish_multi_candidate_fans_out_apply_step(tmp_path, monkeypatch):
    figure = tmp_path / "figure.png"
    _write_figure(figure)
    output = tmp_path / "out" / "final.png"
    vlm = _FakeVLM()
    image_gen = _FakeEditImageGen()
    _patch_providers(monkeypatch, vlm, image_gen)

    result = runner.invoke(
        app,
        [
            "polish",
            "--input",
            str(figure),
            "--output",
            str(output),
            "--num-candidates",
            "3",
            "--legacy-connections",
        ],
    )

    assert result.exit_code == 0, _strip_ansi(result.output)
    # One suggest call, three parallel apply calls
    assert vlm.calls == 1
    assert len(image_gen.calls) == 3
    assert output.exists()
    for k in range(1, 4):
        assert (tmp_path / "out" / "candidates" / f"cand_{k}" / "polished_iter_1.png").exists()


def test_polish_help_documents_flags():
    result = runner.invoke(
        app,
        ["polish", "--help"],
        terminal_width=200,
        color=False,
        env={"COLUMNS": "200", "NO_COLOR": "1", "TERM": "dumb"},
    )
    assert result.exit_code == 0
    out = _strip_ansi(result.output)
    for flag in ("--input", "--venue", "--output", "--iterations", "--aspect-ratio", "--budget"):
        assert flag in out
