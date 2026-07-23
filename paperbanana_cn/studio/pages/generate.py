"""Primary methodology-diagram and statistical-plot workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperbanana_cn.connections.models import ConnectionRole
from paperbanana_cn.i18n import get_translator, localize_error
from paperbanana_cn.studio.components.options import (
    GenerationOptionControls,
    create_generation_options,
    make_run_options,
    option_inputs,
)
from paperbanana_cn.studio.components.results import create_result_image
from paperbanana_cn.studio.components.shell import HeaderComponents
from paperbanana_cn.studio.connections_ui import resolve_image_options
from paperbanana_cn.studio.context import StudioContext, optional_upload_path
from paperbanana_cn.studio.runner import (
    ASPECT_RATIO_CHOICES,
    REFERENCE_CATEGORY_CHOICES,
    merge_context,
    run_methodology,
    run_plot,
)


@dataclass(frozen=True)
class DiagramPage:
    aspect_ratio: Any
    options: GenerationOptionControls
    size_preview: Any
    generate_button: Any
    connection_gate: Any
    configure_button: Any


def _start_run(gr, message: str):
    return gr.update(interactive=False), message, gr.update(open=True)


def _finish_run(gr):
    return gr.update(interactive=True)


def _image_metadata(path: str | None) -> str:
    if not path or not Path(path).is_file():
        return ""
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
        return f"{width} x {height} px"
    except OSError:
        return ""


def build_diagram_page(gr, ctx: StudioContext, header: HeaderComponents) -> DiagramPage:
    config = ctx.manager.load()
    connections_ready = ctx.has_active_connections((ConnectionRole.VLM, ConnectionRole.IMAGE))
    initial = resolve_image_options(
        ctx.manager,
        config.active_image_profile_id,
        config.last_aspect_ratio,
        config.last_output_resolution,
        ctx.t,
    )
    with gr.Row(elem_id="diagram-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_id="diagram-input-panel", elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                with gr.Row(
                    visible=not connections_ready,
                    elem_id="diagram-connection-gate",
                    elem_classes="connection-required",
                ) as connection_gate:
                    gr.Markdown(ctx.t("studio.connection_required"))
                    configure_button = gr.Button(
                        ctx.t("button.open_settings"),
                        size="sm",
                        elem_id="diagram-open-settings",
                        elem_classes="secondary-action",
                    )
                context_text = gr.Textbox(
                    label=ctx.t("field.context"),
                    lines=8,
                    placeholder=ctx.t("placeholder.context"),
                    elem_id="diagram-context",
                )
                context_file = gr.File(
                    label=ctx.t("field.context_file"),
                    file_types=[".txt", ".md"],
                    height=132,
                    elem_id="diagram-context-file",
                    elem_classes="compact-file-upload",
                )
                caption = gr.Textbox(
                    label=ctx.t("field.caption"),
                    lines=2,
                    placeholder=ctx.t("placeholder.caption"),
                    elem_id="diagram-caption",
                )
                with gr.Row(elem_classes="single-control-row"):
                    aspect = gr.Dropdown(
                        label=ctx.t("field.aspect_ratio"),
                        choices=initial.ratios,
                        value=initial.selected_ratio,
                        elem_id="diagram-aspect-ratio",
                    )
                size_preview = gr.Markdown(initial.preview, elem_id="diagram-size-preview")
                options = create_generation_options(
                    gr,
                    ctx,
                    prefix="diagram",
                    resolution_choices=[(item.upper(), item) for item in initial.resolutions],
                    resolution_value=initial.selected_resolution,
                )
                with gr.Accordion(ctx.t("field.reference_category"), open=False):
                    reference_categories = gr.Dropdown(
                        label=ctx.t("field.reference_category"),
                        choices=REFERENCE_CATEGORY_CHOICES,
                        value=[],
                        multiselect=True,
                        info=ctx.t("help.reference_category"),
                    )
                    reference_ids = gr.Textbox(
                        label=ctx.t("field.reference_ids"),
                        placeholder=ctx.t("placeholder.reference_ids"),
                        info=ctx.t("help.reference_ids"),
                    )
                validation = gr.Markdown(
                    "", elem_id="diagram-validation", elem_classes="validation"
                )
            generate = gr.Button(
                ctx.t("button.generate_diagram"),
                variant="primary",
                interactive=connections_ready,
                elem_id="diagram-generate",
                elem_classes="primary-action",
            )

        with gr.Column(elem_id="diagram-result-panel", elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('studio.result_canvas')}")
                status = gr.Markdown(
                    ctx.t("studio.status_ready"),
                    elem_id="diagram-status",
                    elem_classes="run-status",
                )
            result = create_result_image(
                gr,
                label=ctx.t("field.final_diagram"),
                empty_message=ctx.t("empty.generated_result"),
                elem_id="diagram-result",
            )
            result_meta = gr.Markdown("", elem_id="diagram-result-meta", elem_classes="result-meta")
            gallery = gr.Gallery(
                label=ctx.t("field.iterations"),
                columns=5,
                height=150,
                object_fit="contain",
                elem_id="diagram-iterations",
                elem_classes="iteration-strip empty-result-surface",
            )
            with gr.Accordion(
                ctx.t("field.progress"), open=False, elem_id="diagram-log-panel"
            ) as log_panel:
                progress = gr.Textbox(
                    label=ctx.t("field.progress"),
                    lines=9,
                    show_label=False,
                    elem_id="diagram-progress",
                    elem_classes="progress-log",
                )

    def do_diagram(
        vlm_profile,
        image_profile,
        output_format,
        resolution,
        iterations,
        auto_refine,
        max_iterations,
        optimize_inputs,
        save_prompts,
        seed,
        text,
        file,
        figure_caption,
        aspect_ratio,
        ref_categories,
        ref_ids,
        locale,
    ):
        source = merge_context(text, optional_upload_path(file))
        if not source.strip():
            return (
                ctx.t("error.context_empty"),
                "",
                None,
                "",
                [],
                ctx.t("studio.status_error"),
                gr.update(open=False),
            )
        if not (figure_caption or "").strip():
            return (
                ctx.t("error.caption_required"),
                "",
                None,
                "",
                [],
                ctx.t("studio.status_error"),
                gr.update(open=False),
            )
        try:
            run_options = make_run_options(
                ctx,
                vlm_profile_id=vlm_profile,
                image_profile_id=image_profile,
                output_format=output_format,
                output_resolution=resolution,
                iterations=iterations,
                auto_refine=auto_refine,
                max_iterations=max_iterations,
                optimize_inputs=optimize_inputs,
                save_prompts=save_prompts,
                seed=seed,
            )
            settings = ctx.resolve_settings(run_options, (ConnectionRole.VLM, ConnectionRole.IMAGE))
            categories = [item for item in (ref_categories or []) if item]
            if categories:
                settings.reference_category = categories
            log, image, iterations_gallery, error = run_methodology(
                settings,
                source,
                figure_caption,
                aspect_ratio,
                reference_ids=ref_ids or None,
                verbose_logging=False,
                locale=locale,
            )
            return (
                "",
                log,
                None if error else image,
                _image_metadata(None if error else image),
                iterations_gallery,
                ctx.t("studio.status_error") if error else ctx.t("studio.status_complete"),
                gr.update(open=bool(error)),
            )
        except Exception as exc:
            message = localize_error(exc, get_translator(locale))
            return (
                message,
                message,
                None,
                "",
                [],
                ctx.t("studio.status_error"),
                gr.update(open=True),
            )

    started = generate.click(
        lambda: _start_run(gr, ctx.t("studio.status_running")),
        outputs=[generate, status, log_panel],
        queue=False,
    )
    completed = started.then(
        do_diagram,
        inputs=[
            header.vlm_profile,
            header.image_profile,
            *option_inputs(options),
            context_text,
            context_file,
            caption,
            aspect,
            reference_categories,
            reference_ids,
            header.locale,
        ],
        outputs=[validation, progress, result, result_meta, gallery, status, log_panel],
    )
    completed.then(lambda: _finish_run(gr), outputs=[generate], queue=False)
    return DiagramPage(
        aspect,
        options,
        size_preview,
        generate,
        connection_gate,
        configure_button,
    )


def build_plot_page(gr, ctx: StudioContext, header: HeaderComponents) -> Any:
    with gr.Row(elem_id="plot-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_id="plot-input-panel", elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                data_file = gr.File(
                    label=ctx.t("field.data_file"),
                    file_types=[".csv", ".json"],
                    height=132,
                    elem_id="plot-data-file",
                    elem_classes="compact-file-upload",
                )
                intent = gr.Textbox(
                    label=ctx.t("field.intent"),
                    lines=4,
                    placeholder=ctx.t("placeholder.intent"),
                    elem_id="plot-intent",
                )
                aspect = gr.Dropdown(
                    label=ctx.t("field.aspect_ratio"),
                    choices=ASPECT_RATIO_CHOICES,
                    value=ctx.manager.load().last_aspect_ratio,
                    elem_id="plot-aspect-ratio",
                )
                options = create_generation_options(gr, ctx, prefix="plot")
                validation = gr.Markdown("", elem_id="plot-validation", elem_classes="validation")
            generate = gr.Button(
                ctx.t("button.generate_plot"),
                variant="primary",
                interactive=ctx.has_active_connections((ConnectionRole.VLM,)),
                elem_id="plot-generate",
                elem_classes="primary-action",
            )
        with gr.Column(elem_id="plot-result-panel", elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('studio.result_canvas')}")
                status = gr.Markdown(ctx.t("studio.status_ready"), elem_classes="run-status")
            result = create_result_image(
                gr,
                label=ctx.t("field.final_plot"),
                empty_message=ctx.t("empty.generated_result"),
                elem_id="plot-result",
            )
            result_meta = gr.Markdown("", elem_classes="result-meta")
            gallery = gr.Gallery(
                label=ctx.t("field.iterations"),
                columns=5,
                height=150,
                elem_classes="iteration-strip empty-result-surface",
            )
            with gr.Accordion(ctx.t("field.progress"), open=False) as log_panel:
                progress = gr.Textbox(lines=9, show_label=False, elem_classes="progress-log")

    def do_plot(
        vlm_profile,
        output_format,
        iterations,
        auto_refine,
        max_iterations,
        optimize_inputs,
        save_prompts,
        seed,
        upload,
        plot_intent,
        aspect_ratio,
        locale,
    ):
        path = optional_upload_path(upload)
        if not path:
            return (
                ctx.t("error.data_required"),
                "",
                None,
                "",
                [],
                ctx.t("studio.status_error"),
                gr.update(open=False),
            )
        if not (plot_intent or "").strip():
            return (
                ctx.t("error.intent_required"),
                "",
                None,
                "",
                [],
                ctx.t("studio.status_error"),
                gr.update(open=False),
            )
        try:
            run_options = make_run_options(
                ctx,
                vlm_profile_id=vlm_profile,
                output_format=output_format,
                iterations=iterations,
                auto_refine=auto_refine,
                max_iterations=max_iterations,
                optimize_inputs=optimize_inputs,
                save_prompts=save_prompts,
                seed=seed,
            )
            settings = ctx.resolve_settings(run_options, (ConnectionRole.VLM,))
            log, image, iterations_gallery, error = run_plot(
                settings,
                path,
                plot_intent,
                aspect_ratio,
                verbose_logging=False,
                locale=locale,
            )
            return (
                "",
                log,
                None if error else image,
                _image_metadata(None if error else image),
                iterations_gallery,
                ctx.t("studio.status_error") if error else ctx.t("studio.status_complete"),
                gr.update(open=bool(error)),
            )
        except Exception as exc:
            message = localize_error(exc, get_translator(locale))
            return (
                message,
                message,
                None,
                "",
                [],
                ctx.t("studio.status_error"),
                gr.update(open=True),
            )

    started = generate.click(
        lambda: _start_run(gr, ctx.t("studio.status_running")),
        outputs=[generate, status, log_panel],
        queue=False,
    )
    completed = started.then(
        do_plot,
        inputs=[
            header.vlm_profile,
            *option_inputs(options),
            data_file,
            intent,
            aspect,
            header.locale,
        ],
        outputs=[validation, progress, result, result_meta, gallery, status, log_panel],
    )
    completed.then(lambda: _finish_run(gr), outputs=[generate], queue=False)
    return generate


def bind_image_options(gr, ctx: StudioContext, header: HeaderComponents, page: DiagramPage) -> None:
    if page.options.resolution is None:
        return

    def update_options(profile_id, aspect, resolution, locale):
        state = resolve_image_options(
            ctx.manager,
            profile_id,
            aspect,
            resolution,
            get_translator(locale),
        )
        return (
            gr.update(choices=state.ratios, value=state.selected_ratio),
            gr.update(
                choices=[(item.upper(), item) for item in state.resolutions],
                value=state.selected_resolution,
            ),
            state.preview,
        )

    outputs = [page.aspect_ratio, page.options.resolution, page.size_preview]
    inputs = [header.image_profile, page.aspect_ratio, page.options.resolution, header.locale]
    header.image_profile.change(update_options, inputs=inputs, outputs=outputs)
    page.aspect_ratio.change(
        lambda value: ctx.manager.save_preferences(aspect_ratio=value),
        inputs=[page.aspect_ratio],
    ).then(update_options, inputs=inputs, outputs=outputs)
    page.options.resolution.change(
        lambda value: ctx.manager.save_preferences(output_resolution=value),
        inputs=[page.options.resolution],
    ).then(update_options, inputs=inputs, outputs=outputs)
    header.locale.change(update_options, inputs=inputs, outputs=outputs, queue=False)
