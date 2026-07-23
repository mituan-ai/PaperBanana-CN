"""PaperBanana Studio — local browser UI for diagram, plot, and evaluation workflows."""

from __future__ import annotations

__all__ = ["launch_studio", "build_studio_app", "build_studio_server_app"]


def launch_studio(**kwargs):
    """Start the Gradio studio included in the default installation."""
    from paperbanana_cn.studio.app import launch_studio as _launch

    return _launch(**kwargs)


def build_studio_app(**kwargs):
    """Build the Gradio Blocks app without launching (for tests and embedding)."""
    from paperbanana_cn.studio.app import build_studio_app as _build

    return _build(**kwargs)


def build_studio_server_app(**kwargs):
    """Build the bilingual FastAPI app without starting a server."""
    from paperbanana_cn.studio.app import build_studio_server_app as _build

    return _build(**kwargs)
