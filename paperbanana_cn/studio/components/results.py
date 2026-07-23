"""Stable result surfaces for Gradio output images."""

from __future__ import annotations

from typing import Any


def create_result_image(
    gr,
    *,
    label: str,
    empty_message: str,
    elem_id: str,
    image_classes: str = "result-canvas",
    stage_classes: str = "result-stage",
    height: int | None = None,
) -> Any:
    """Create an output image with a visible, translatable empty state."""
    with gr.Column(
        elem_id=f"{elem_id}-stage",
        elem_classes=stage_classes,
    ):
        image = gr.Image(
            label=label,
            type="filepath",
            height=height,
            elem_id=elem_id,
            elem_classes=image_classes,
        )
        gr.Markdown(
            empty_message,
            elem_id=f"{elem_id}-empty",
            elem_classes="result-empty-state",
        )
    return image
