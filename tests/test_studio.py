"""Tests for PaperBanana Studio (Gradio UI)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "fn",
    [
        "list_run_ids",
        "list_batch_ids",
        "load_run_summary",
        "load_batch_summary",
    ],
)
def test_runs_helpers_smoke(fn: str, tmp_path):
    from paperbanana.studio import runs as runs_mod

    f = getattr(runs_mod, fn)
    if fn.startswith("load_"):
        out = f(str(tmp_path), "missing_id")
        assert isinstance(out, dict)
        assert out.get("exists") is False
    else:
        assert f(str(tmp_path)) == []


def test_build_settings_merge(tmp_path):
    from paperbanana.studio.runner import build_settings

    s = build_settings(
        config_path=None,
        output_dir=str(tmp_path / "out"),
        vlm_provider="gemini",
        vlm_model="gemini-2.0-flash",
        image_provider="google_imagen",
        image_model="gemini-3-pro-image-preview",
        output_format="png",
        refinement_iterations=2,
        auto_refine=False,
        max_iterations=10,
        optimize_inputs=True,
        save_prompts=False,
        legacy_connections=True,
    )
    assert s.output_dir == str(tmp_path / "out")
    assert s.refinement_iterations == 2
    assert s.optimize_inputs is True


def test_vlm_only_settings_do_not_require_image_connection(tmp_path):
    from paperbanana.connections.manager import ConnectionManager
    from paperbanana.connections.models import ConnectionProfile, ConnectionRole
    from paperbanana.studio.runner import build_settings

    manager = ConnectionManager(tmp_path / "connections.json", tmp_path / "secrets.json")
    vlm = ConnectionProfile(
        name="VLM only",
        role=ConnectionRole.VLM,
        provider="openai",
        model="vision-model",
    )
    manager.save_profile(vlm, api_key="test-secret")

    settings = build_settings(
        config_path=None,
        output_dir=str(tmp_path / "out"),
        vlm_provider="",
        vlm_model="",
        image_provider="",
        image_model="",
        output_format="png",
        refinement_iterations=2,
        auto_refine=False,
        max_iterations=10,
        optimize_inputs=False,
        save_prompts=True,
        connection_manager=manager,
        required_roles=(ConnectionRole.VLM,),
    )

    assert settings.vlm_model == "vision-model"
    assert settings.image_provider == "none"
    assert settings.image_api_key is None


def test_workflow_specs_and_dynamic_roles(tmp_path):
    from paperbanana.connections.models import ConnectionRole
    from paperbanana.studio.models import (
        WORKFLOW_BY_KEY,
        roles_for_batch_type,
        roles_for_saved_run,
    )

    assert WORKFLOW_BY_KEY["diagram"].required_roles == (
        ConnectionRole.VLM,
        ConnectionRole.IMAGE,
    )
    assert WORKFLOW_BY_KEY["plot"].required_roles == (ConnectionRole.VLM,)
    assert WORKFLOW_BY_KEY["composite"].required_roles == ()
    assert roles_for_batch_type("statistical_plot") == (ConnectionRole.VLM,)

    run_dir = tmp_path / "run_plot"
    run_dir.mkdir()
    (run_dir / "run_input.json").write_text(
        '{"diagram_type": "statistical_plot"}', encoding="utf-8"
    )
    assert roles_for_saved_run(str(tmp_path), "run_plot") == (ConnectionRole.VLM,)


def test_build_studio_app():
    gradio = pytest.importorskip("gradio")
    from paperbanana.studio.app import build_studio_app

    _ = gradio
    demo = build_studio_app(default_output_dir="outputs", config_path=None)
    assert demo is not None


def test_studio_server_mounts_one_single_page_app(tmp_path):
    from fastapi.testclient import TestClient

    from paperbanana.connections.manager import ConnectionManager
    from paperbanana.studio.app import build_studio_server_app
    from paperbanana.studio.branding import BRAND_LOGO_PATH

    manager = ConnectionManager(tmp_path / "connections.json", tmp_path / "secrets.json")
    app = build_studio_server_app(connection_manager=manager, server_port=7788)
    with TestClient(app, follow_redirects=False) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert "location" not in root.headers
        assert client.get("/zh-CN/").status_code == 404
        assert client.get("/en/").status_code == 404
        expected_logo = BRAND_LOGO_PATH.read_bytes()
        brand_logo = client.get("/paperbanana-assets/paperbanana-cn-logo.jpg")
        favicon = client.get("/favicon.ico")
        assert brand_logo.status_code == 200
        assert favicon.status_code == 200
        assert brand_logo.headers["content-type"] == "image/jpeg"
        assert favicon.headers["content-type"] == "image/jpeg"
        assert brand_logo.content == expected_logo
        assert favicon.content == expected_logo


def test_launch_studio_share_uses_gradio_620_tunnel_signature(monkeypatch):
    import gradio.networking
    import uvicorn

    from paperbanana.studio import app as app_module

    tunnel_args = {}

    class FakeServer:
        def __init__(self, _config):
            self.started = False
            self.should_exit = False

        def run(self):
            self.started = True

    def fake_setup_tunnel(**kwargs):
        tunnel_args.update(kwargs)
        return "https://studio.example"

    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    monkeypatch.setattr(gradio.networking, "setup_tunnel", fake_setup_tunnel)
    monkeypatch.setattr(app_module.secrets, "token_urlsafe", lambda _size: "share-token")

    app_module.launch_studio(host="127.0.0.1", port=7788, share=True)

    assert tunnel_args == {
        "local_host": "127.0.0.1",
        "local_port": 7788,
        "share_token": "share-token",
        "share_server_address": None,
        "share_server_tls_certificate": None,
    }


def test_studio_defaults_persist_without_form_state(tmp_path):
    from paperbanana.connections.manager import ConnectionManager

    manager = ConnectionManager(tmp_path / "connections.json", tmp_path / "secrets.json")
    manager.save_studio_defaults(output_dir="/tmp/paperbanana-runs", config_path="config.yaml")
    reloaded = manager.load()
    assert reloaded.studio_output_dir == "/tmp/paperbanana-runs"
    assert reloaded.studio_config_path == "config.yaml"


def test_image_options_follow_provider_capabilities(tmp_path):
    from paperbanana.connections.manager import ConnectionManager
    from paperbanana.connections.models import ConnectionProfile, ConnectionRole
    from paperbanana.i18n import get_translator
    from paperbanana.studio.connections_ui import resolve_image_options

    manager = ConnectionManager(tmp_path / "connections.json", tmp_path / "secrets.json")
    fixed = ConnectionProfile(
        name="fixed",
        role=ConnectionRole.IMAGE,
        provider="openai_imagen",
        model="gpt-image-1.5",
        image_size_mode="fixed",
    )
    explicit = fixed.model_copy(
        update={"id": "explicit", "name": "explicit", "image_size_mode": "explicit_pixels"}
    )
    manager.save_profile(fixed, api_key="key")
    manager.save_profile(explicit, api_key="key")
    t = get_translator("en")

    fixed_options = resolve_image_options(manager, fixed.id, "4:5", "4k", t)
    assert fixed_options.ratios == ["1:1", "3:2", "2:3"]
    assert fixed_options.resolutions == ["1k"]
    assert fixed_options.selected_ratio is None
    assert "unsupported" in fixed_options.preview

    explicit_options = resolve_image_options(manager, explicit.id, "4:5", "4k", t)
    assert len(explicit_options.ratios) == 10
    assert explicit_options.resolutions == ["1k", "2k", "4k"]
    assert explicit_options.selected_ratio == "4:5"
    assert explicit_options.selected_resolution == "4k"
    assert "px" in explicit_options.preview


def test_studio_batch_reuses_shared_runner_and_localizes_summary(tmp_path, monkeypatch):
    from paperbanana.core.config import Settings
    from paperbanana.studio.runner import run_batch

    captured = {}

    def _fake_shared(**kwargs):
        captured.update(kwargs)
        kwargs["progress_callback"]("Item 1/1 figure-1: ok -> /tmp/result.png")
        return {
            "batch_dir": str(tmp_path / "batch_1"),
            "batch_report_path": str(tmp_path / "batch_1" / "batch_report.json"),
            "succeeded": 1,
            "failed": 0,
            "skipped": 0,
        }

    monkeypatch.setattr("paperbanana.core.workflow_runner.run_methodology_batch", _fake_shared)
    settings = Settings(output_dir=str(tmp_path))
    log, batch_dir = run_batch(
        settings,
        str(tmp_path / "manifest.json"),
        locale="zh-CN",
    )

    assert captured["runtime_settings"] is settings
    assert "成功" in log
    assert "批处理完成" in log
    assert batch_dir.endswith("batch_1")


def test_run_composite_smoke(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    Image.new("RGB", (100, 80), (255, 0, 0)).save(str(p1))
    Image.new("RGB", (100, 80), (0, 255, 0)).save(str(p2))

    out_dir = tmp_path / "out"
    log, output_path = run_composite(
        [str(p1), str(p2)],
        output_dir=str(out_dir),
        layout="1x2",
        output_filename="result.png",
    )
    assert output_path is not None
    assert (out_dir / "result.png").exists()
    assert "Done." in log


def test_run_composite_no_files_returns_error(tmp_path):
    from paperbanana.studio.runner import run_composite

    log, output_path = run_composite(
        [],
        output_dir=str(tmp_path),
    )
    assert output_path is None
    assert "No valid image" in log


def test_run_composite_invalid_label_position(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p = tmp_path / "x.png"
    Image.new("RGB", (50, 50), (0, 0, 255)).save(str(p))
    log, output_path = run_composite(
        [str(p)],
        output_dir=str(tmp_path),
        label_position="left",
    )
    assert output_path is None
    assert "label_position" in log


def test_run_composite_explicit_labels(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    Image.new("RGB", (60, 60), (255, 0, 0)).save(str(p1))
    Image.new("RGB", (60, 60), (0, 255, 0)).save(str(p2))

    log, output_path = run_composite(
        [str(p1), str(p2)],
        output_dir=str(tmp_path / "out"),
        labels="Fig A, Fig B",
        layout="1x2",
    )
    assert output_path is not None
    assert "Done." in log


def test_run_composite_disable_labels(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p = tmp_path / "x.png"
    Image.new("RGB", (60, 60), (0, 0, 255)).save(str(p))
    log, output_path = run_composite(
        [str(p)],
        output_dir=str(tmp_path / "out"),
        labels="none",
    )
    assert output_path is not None
    assert "Done." in log


def test_run_composite_zero_spacing_allowed(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    Image.new("RGB", (40, 40), (255, 0, 0)).save(str(p1))
    Image.new("RGB", (40, 40), (0, 255, 0)).save(str(p2))

    log, output_path = run_composite(
        [str(p1), str(p2)],
        output_dir=str(tmp_path / "out"),
        layout="1x2",
        spacing=0,
    )
    assert output_path is not None
    assert "Done." in log


def test_run_composite_negative_spacing_rejected(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p = tmp_path / "x.png"
    Image.new("RGB", (40, 40), (255, 0, 0)).save(str(p))
    log, output_path = run_composite(
        [str(p)],
        output_dir=str(tmp_path / "out"),
        spacing=-5,
    )
    assert output_path is None
    assert "spacing" in log


def test_run_composite_invalid_font_size_rejected(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p = tmp_path / "x.png"
    Image.new("RGB", (40, 40), (255, 0, 0)).save(str(p))
    log, output_path = run_composite(
        [str(p)],
        output_dir=str(tmp_path / "out"),
        label_font_size=0,
    )
    assert output_path is None
    assert "label_font_size" in log


def test_run_composite_path_traversal_sanitized(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p = tmp_path / "x.png"
    Image.new("RGB", (40, 40), (255, 0, 0)).save(str(p))

    out_dir = tmp_path / "out"
    log, output_path = run_composite(
        [str(p)],
        output_dir=str(out_dir),
        output_filename="../escape.png",
    )
    assert output_path is not None
    # Output must stay inside the configured output_dir
    assert Path(output_path).parent.resolve() == out_dir.resolve()
    assert Path(output_path).name == "escape.png"
    assert not (tmp_path / "escape.png").exists()


def test_run_composite_dotdot_filename_falls_back(tmp_path):
    from PIL import Image

    from paperbanana.studio.runner import run_composite

    p = tmp_path / "x.png"
    Image.new("RGB", (40, 40), (255, 0, 0)).save(str(p))

    out_dir = tmp_path / "out"
    log, output_path = run_composite(
        [str(p)],
        output_dir=str(out_dir),
        output_filename="..",
    )
    assert output_path is not None
    assert Path(output_path).name == "composite.png"


def test_run_orchestration_requires_paper_or_resume(tmp_path):
    from paperbanana.core.config import Settings
    from paperbanana.studio.runner import run_orchestration

    s = Settings().model_copy(update={"output_dir": str(tmp_path)})
    log, orch, plan, pkg = run_orchestration(
        s,
        paper_file_path=None,
        resume_orchestrate=None,
        data_dir=None,
        max_method_figures=2,
        max_plot_figures=1,
        pdf_pages=None,
        dry_run=True,
        venue="neurips",
        retry_failed=False,
        max_retries=0,
        concurrency=1,
        config_path=None,
        verbose_logging=False,
    )
    assert "Error:" in log
    assert orch == "" and plan == "" and pkg == ""


def test_run_orchestration_rejects_paper_plus_resume(tmp_path):
    from paperbanana.core.config import Settings
    from paperbanana.studio.runner import run_orchestration

    paper = tmp_path / "p.txt"
    paper.write_text("hello", encoding="utf-8")
    s = Settings().model_copy(update={"output_dir": str(tmp_path)})
    log, orch, plan, pkg = run_orchestration(
        s,
        paper_file_path=str(paper),
        resume_orchestrate="orchestrate_x",
        data_dir=None,
        max_method_figures=2,
        max_plot_figures=0,
        pdf_pages=None,
        dry_run=True,
        venue="neurips",
        retry_failed=False,
        max_retries=0,
        concurrency=1,
        config_path=None,
        verbose_logging=False,
    )
    assert "clear the paper upload" in log.lower()
    assert orch == ""


def test_preview_json_file_truncates(tmp_path):
    from paperbanana.studio import runner as runner_mod

    p = tmp_path / "big.json"
    p.write_text('{"x": "' + ("a" * 20_000) + '"}', encoding="utf-8")
    prev = runner_mod._preview_json_file(p, max_chars=100)
    assert "truncated" in prev
    assert len(prev) <= 150


def test_run_evaluate_plot_requires_data_file(tmp_path):
    """Plot evaluation mode validates data path before provider setup."""
    from paperbanana.core.config import Settings
    from paperbanana.core.types import DiagramType
    from paperbanana.studio.runner import run_evaluate

    generated = tmp_path / "g.png"
    reference = tmp_path / "r.png"
    generated.write_bytes(b"x")
    reference.write_bytes(b"y")

    log, result = run_evaluate(
        Settings(),
        generated_path=str(generated),
        reference_path=str(reference),
        source_context="",
        caption="Plot intent",
        evaluation_task=DiagramType.STATISTICAL_PLOT,
        plot_data_path=str(tmp_path / "missing.csv"),
    )
    assert "Plot data file not found" in log
    assert "Plot data file not found" in result
