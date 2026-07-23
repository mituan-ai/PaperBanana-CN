"""Factories for separate per-workflow option components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paperbanana.studio.context import StudioContext, optional_int
from paperbanana.studio.models import StudioRunOptions


@dataclass(frozen=True)
class GenerationOptionControls:
    output_format: Any
    resolution: Any | None
    iterations: Any
    auto_refine: Any
    max_iterations: Any
    optimize_inputs: Any
    save_prompts: Any
    seed: Any


def create_generation_options(
    gr,
    ctx: StudioContext,
    *,
    prefix: str,
    resolution_choices: list[tuple[str, str]] | None = None,
    resolution_value: str | None = None,
) -> GenerationOptionControls:
    """Create new components for one page; component instances are never shared."""
    with gr.Row(elem_classes="generation-options-row", equal_height=True):
        output_format = gr.Dropdown(
            label=ctx.t("settings.output_format"),
            choices=["png", "jpeg", "webp"],
            value="png",
            scale=1,
            min_width=0,
            elem_id=f"{prefix}-output-format",
        )
        resolution = None
        if resolution_choices is not None:
            resolution = gr.Dropdown(
                label=ctx.t("settings.resolution"),
                choices=resolution_choices,
                value=resolution_value,
                scale=1,
                min_width=0,
                elem_id=f"{prefix}-resolution",
            )
        iterations = gr.Number(
            label=ctx.t("settings.iterations"),
            value=3,
            precision=0,
            minimum=1,
            scale=1,
            min_width=0,
            elem_id=f"{prefix}-refinement-iterations",
        )
    auto_refine = gr.Checkbox(
        label=ctx.t("settings.auto_refine"),
        value=False,
        elem_id=f"{prefix}-auto-refine",
    )
    with gr.Accordion(
        ctx.t("studio.advanced_settings"),
        open=False,
        elem_id=f"{prefix}-advanced-settings",
    ):
        max_iterations = gr.Number(
            label=ctx.t("settings.max_iterations"),
            value=30,
            precision=0,
            minimum=1,
            elem_id=f"{prefix}-max-iterations",
        )
        optimize_inputs = gr.Checkbox(
            label=ctx.t("settings.optimize"),
            value=False,
            elem_id=f"{prefix}-optimize-inputs",
        )
        save_prompts = gr.Checkbox(
            label=ctx.t("settings.save_prompts"),
            value=True,
            elem_id=f"{prefix}-save-prompts",
        )
        seed = gr.Number(
            label=ctx.t("settings.seed"),
            value=None,
            precision=0,
            info=ctx.t("settings.seed_help"),
            elem_id=f"{prefix}-seed",
        )
    return GenerationOptionControls(
        output_format,
        resolution,
        iterations,
        auto_refine,
        max_iterations,
        optimize_inputs,
        save_prompts,
        seed,
    )


def option_inputs(controls: GenerationOptionControls) -> list[Any]:
    values = [controls.output_format]
    if controls.resolution is not None:
        values.append(controls.resolution)
    values.extend(
        [
            controls.iterations,
            controls.auto_refine,
            controls.max_iterations,
            controls.optimize_inputs,
            controls.save_prompts,
            controls.seed,
        ]
    )
    return values


def make_run_options(
    ctx: StudioContext,
    *,
    vlm_profile_id: str | None,
    image_profile_id: str | None = None,
    output_format: str = "png",
    output_resolution: str = "2k",
    iterations: float = 3,
    auto_refine: bool = False,
    max_iterations: float = 30,
    optimize_inputs: bool = False,
    save_prompts: bool = True,
    seed: float | None = None,
) -> StudioRunOptions:
    config = ctx.manager.load()
    return StudioRunOptions(
        output_dir=config.studio_output_dir or ctx.default_output_dir,
        config_path=config.studio_config_path or ctx.default_config_path or None,
        vlm_profile_id=vlm_profile_id or None,
        image_profile_id=image_profile_id or None,
        output_format=output_format,
        output_resolution=output_resolution,
        refinement_iterations=max(1, int(iterations)),
        auto_refine=bool(auto_refine),
        max_iterations=max(1, int(max_iterations)),
        optimize_inputs=bool(optimize_inputs),
        save_prompts=bool(save_prompts),
        seed=optional_int(seed),
    )


def default_run_options(
    ctx: StudioContext,
    *,
    vlm_profile_id: str | None = None,
    image_profile_id: str | None = None,
) -> StudioRunOptions:
    return make_run_options(
        ctx,
        vlm_profile_id=vlm_profile_id,
        image_profile_id=image_profile_id,
    )
