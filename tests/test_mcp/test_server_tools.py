"""Smoke tests for the MCP server tool surface.

These guard against tools silently dropping out of registration (e.g. a
decorator typo or an import error in a tool module) and keep the public
tool list in sync with the docs.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("fastmcp", reason="mcp extra not installed")

from mcp_server.server import mcp  # noqa: E402

EXPECTED_TOOLS = {
    "batch_diagrams",
    "batch_plots",
    "continue_diagram",
    "continue_plot",
    "continue_run",
    "download_references",
    "evaluate_diagram",
    "evaluate_plot",
    "generate_diagram",
    "generate_plot",
    "orchestrate_figures",
}


def _list_tools():
    return asyncio.run(mcp.list_tools())


def test_all_expected_tools_registered():
    names = {t.name for t in _list_tools()}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"MCP tools missing from registration: {missing}"


def test_no_unexpected_tools():
    """New tools are welcome — add them to EXPECTED_TOOLS and the README."""
    names = {t.name for t in _list_tools()}
    unexpected = names - EXPECTED_TOOLS
    assert not unexpected, (
        f"New MCP tools {unexpected} — update EXPECTED_TOOLS, the server "
        "docstring, and the README MCP section together."
    )


def test_every_tool_has_description():
    undocumented = [t.name for t in _list_tools() if not (t.description or "").strip()]
    assert not undocumented, f"MCP tools without descriptions: {undocumented}"


def test_generate_diagram_exposes_input_images_param():
    """generate_diagram accepts optional input_images (reference/sketch paths)."""
    tool = next(t for t in _list_tools() if t.name == "generate_diagram")
    assert "input_images" in tool.parameters.get("properties", {})


@pytest.mark.parametrize(
    "tool_name, expected",
    [
        ("generate_diagram", {"vlm_connection", "image_connection", "legacy_connections"}),
        ("generate_plot", {"vlm_connection", "legacy_connections"}),
        ("batch_diagrams", {"vlm_connection", "image_connection", "legacy_connections"}),
        ("batch_plots", {"vlm_connection", "legacy_connections"}),
    ],
)
def test_model_tools_expose_connection_controls(tool_name, expected):
    tool = next(item for item in _list_tools() if item.name == tool_name)
    assert expected <= set(tool.parameters.get("properties", {}))


def test_mcp_profile_resolution_and_vlm_only_role(tmp_path, monkeypatch):
    from mcp_server.server import _mcp_runtime_settings
    from paperbanana_cn.connections import resolver
    from paperbanana_cn.connections.manager import ConnectionManager
    from paperbanana_cn.connections.models import ConnectionProfile, ConnectionRole

    manager = ConnectionManager(
        config_path=tmp_path / "connections.json",
        secret_path=tmp_path / "secrets.json",
    )
    vlm = ConnectionProfile(
        name="vlm",
        role=ConnectionRole.VLM,
        provider="openai",
        base_url="https://vlm.example/v1",
        model="vlm-model",
    )
    image = ConnectionProfile(
        name="image",
        role=ConnectionRole.IMAGE,
        provider="openai_imagen",
        base_url="https://image.example/v1",
        model="image-model",
        image_size_mode="explicit_pixels",
    )
    manager.save_profile(vlm, api_key="vlm-key")
    manager.save_profile(image, api_key="image-key")
    monkeypatch.setattr(resolver, "ConnectionManager", lambda: manager)

    pair = _mcp_runtime_settings(overrides={})
    assert pair.vlm_base_url == "https://vlm.example/v1"
    assert pair.image_base_url == "https://image.example/v1"
    assert pair.effective_vlm_model == "vlm-model"
    assert pair.effective_image_model == "image-model"

    manager.delete_profile(image.id)
    vlm_only = _mcp_runtime_settings(
        overrides={"image_provider": "none"},
        required_roles=(ConnectionRole.VLM,),
    )
    assert vlm_only.vlm_base_url == "https://vlm.example/v1"
    assert vlm_only.image_api_key is None


def test_mcp_rejects_profile_and_legacy_mix():
    from mcp_server.server import _reject_mcp_connection_mix

    with pytest.raises(ValueError, match="cannot be combined"):
        _reject_mcp_connection_mix(
            vlm_connection="saved-vlm",
            image_connection=None,
            legacy_connections=True,
            legacy_provider_options=False,
        )
    with pytest.raises(ValueError, match="legacy_connections=true"):
        _reject_mcp_connection_mix(
            vlm_connection=None,
            image_connection=None,
            legacy_connections=False,
            legacy_provider_options=True,
        )


def test_validate_input_images_rejects_missing_and_non_raster(tmp_path):
    from mcp_server.server import _validate_input_images

    # Missing file
    with pytest.raises(ValueError, match="not found"):
        _validate_input_images([str(tmp_path / "missing.png")])

    # Non-raster file with image extension
    fake = tmp_path / "fake.png"
    fake.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="raster image"):
        _validate_input_images([str(fake)])

    # Valid tiny PNG passes
    from PIL import Image

    real = tmp_path / "real.png"
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(real)
    assert _validate_input_images([str(real)]) == [str(real)]
    assert _validate_input_images(None) == []
