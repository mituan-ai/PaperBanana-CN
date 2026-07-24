"""Evaluation and continue-run workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paperbanana_cn.connections.models import ConnectionRole
from paperbanana_cn.core.types import DiagramType
from paperbanana_cn.i18n import get_translator, localize_error
from paperbanana_cn.studio import runs as runs_mod
from paperbanana_cn.studio.components.options import default_run_options
from paperbanana_cn.studio.components.results import create_result_image
from paperbanana_cn.studio.components.shell import HeaderComponents
from paperbanana_cn.studio.context import (
    StudioContext,
    optional_int,
    optional_upload_path,
)
from paperbanana_cn.studio.models import roles_for_saved_run
from paperbanana_cn.studio.runner import merge_context, run_continue, run_evaluate


@dataclass(frozen=True)
class ContinuePage:
    run_id: Any
    run_button: Any


def _bind_busy(gr, button, status, log_panel, ctx, callback, inputs, outputs):
    started = button.click(
        lambda: (
            gr.update(interactive=False),
            ctx.t("studio.status_running"),
            gr.update(open=True),
        ),
        outputs=[button, status, log_panel],
        queue=False,
    )
    completed = started.then(callback, inputs=inputs, outputs=outputs)
    completed.then(lambda: gr.update(interactive=True), outputs=[button], queue=False)


def build_evaluate_page(gr, ctx: StudioContext, header: HeaderComponents) -> Any:
    with gr.Row(elem_id="evaluate-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_id="evaluate-input-panel", elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                target = gr.Radio(
                    label=ctx.t("field.evaluation_target"),
                    choices=[
                        (ctx.t("choice.methodology"), "methodology"),
                        (ctx.t("choice.statistical_plot"), "statistical_plot"),
                    ],
                    value="methodology",
                    elem_id="evaluate-target",
                    elem_classes="segmented-control",
                )
                generated = gr.Image(
                    label=ctx.t("field.generated_image"),
                    type="filepath",
                    height=164,
                    sources=["upload"],
                    elem_id="evaluate-generated-image",
                    elem_classes="compact-image-upload",
                )
                reference = gr.Image(
                    label=ctx.t("field.human_reference"),
                    type="filepath",
                    height=164,
                    sources=["upload"],
                    elem_id="evaluate-reference-image",
                    elem_classes="compact-image-upload",
                )
                source_context = gr.Textbox(label=ctx.t("field.source_context"), lines=4)
                context_file = gr.File(
                    label=ctx.t("field.context_file"),
                    file_types=[".txt", ".md"],
                    height=116,
                    elem_classes="compact-file-upload",
                )
                plot_data = gr.File(
                    label=ctx.t("field.plot_evaluation_data"),
                    file_types=[".csv", ".json"],
                    height=116,
                    elem_classes="compact-file-upload",
                )
                caption = gr.Textbox(label=ctx.t("field.figure_caption"), lines=2)
                validation = gr.Markdown(
                    "", elem_id="evaluate-validation", elem_classes="validation"
                )
            evaluate = gr.Button(
                ctx.t("button.evaluate"),
                variant="primary",
                interactive=ctx.has_active_connections((ConnectionRole.VLM,)),
                elem_id="evaluate-run",
                elem_classes="primary-action",
            )
        with gr.Column(elem_id="evaluate-result-panel", elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('tab.evaluate')}")
                status = gr.Markdown(ctx.t("studio.status_ready"), elem_classes="run-status")
            result = gr.Markdown(
                ctx.t("empty.evaluation_result"),
                elem_id="evaluate-result",
                elem_classes="evaluation-result empty-result-copy",
            )
            with gr.Accordion(ctx.t("field.log"), open=False) as log_panel:
                log = gr.Textbox(lines=10, show_label=False, elem_classes="progress-log")

    def do_evaluate(
        vlm_profile,
        task_value,
        gen,
        ref,
        text,
        upload,
        data_upload,
        figure_caption,
        locale,
    ):
        if not optional_upload_path(gen) or not optional_upload_path(ref):
            message = ctx.t("error.images_required")
            return message, "", "", ctx.t("studio.status_error"), gr.update(open=False)
        try:
            settings = ctx.resolve_settings(
                default_run_options(ctx, vlm_profile_id=vlm_profile),
                (ConnectionRole.VLM,),
            )
            task = DiagramType(task_value)
            progress, report = run_evaluate(
                settings,
                optional_upload_path(gen) or "",
                optional_upload_path(ref) or "",
                merge_context(text, optional_upload_path(upload)),
                figure_caption or "",
                evaluation_task=task,
                plot_data_path=optional_upload_path(data_upload) or "",
                verbose_logging=False,
                locale=locale,
            )
            return "", progress, report, ctx.t("studio.status_complete"), gr.update(open=False)
        except Exception as exc:
            message = localize_error(exc, get_translator(locale))
            return message, message, message, ctx.t("studio.status_error"), gr.update(open=True)

    _bind_busy(
        gr,
        evaluate,
        status,
        log_panel,
        ctx,
        do_evaluate,
        [
            header.vlm_profile,
            target,
            generated,
            reference,
            source_context,
            context_file,
            plot_data,
            caption,
            header.locale,
        ],
        [validation, log, result, status, log_panel],
    )
    return evaluate


def build_continue_page(gr, ctx: StudioContext, header: HeaderComponents) -> ContinuePage:
    config = ctx.manager.load()
    run_root = config.studio_output_dir or ctx.default_output_dir
    with gr.Row(elem_id="continue-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_id="continue-input-panel", elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                run_id = gr.Dropdown(
                    label=ctx.t("field.run_id"),
                    choices=runs_mod.list_run_ids(run_root),
                    allow_custom_value=True,
                    elem_id="continue-run-id",
                )
                current_result = gr.Image(
                    label=ctx.t("field.latest_result"),
                    type="filepath",
                    height=164,
                    interactive=False,
                    placeholder=ctx.t("empty.selected_run"),
                    elem_id="continue-current-result",
                    elem_classes="compact-history-preview",
                )
                feedback = gr.Textbox(
                    label=ctx.t("field.feedback"),
                    lines=5,
                    placeholder=ctx.t("placeholder.feedback"),
                )
                extra_iterations = gr.Number(
                    label=ctx.t("field.additional_iterations"),
                    value=None,
                    precision=0,
                    info=ctx.t("help.additional_iterations"),
                )
                validation = gr.Markdown(
                    "", elem_id="continue-validation", elem_classes="validation"
                )
            run = gr.Button(
                ctx.t("button.continue"),
                variant="primary",
                interactive=False,
                elem_id="continue-run",
                elem_classes="primary-action",
            )
        with gr.Column(elem_id="continue-result-panel", elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('field.latest_result')}")
                status = gr.Markdown(ctx.t("studio.status_ready"), elem_classes="run-status")
            result = create_result_image(
                gr,
                label=ctx.t("field.latest_result"),
                empty_message=ctx.t("empty.selected_run"),
                elem_id="continue-result",
            )
            gallery = gr.Gallery(
                label=ctx.t("field.new_iterations"),
                columns=5,
                height=150,
                elem_classes="iteration-strip empty-result-surface",
            )
            with gr.Accordion(ctx.t("field.progress"), open=False) as log_panel:
                progress = gr.Textbox(lines=9, show_label=False, elem_classes="progress-log")

    def preview_run(selected_run):
        if not selected_run:
            return None
        summary = runs_mod.load_run_summary(run_root, selected_run)
        return summary.get("final_image") or None

    run_id.change(preview_run, inputs=[run_id], outputs=[current_result], queue=False)

    def do_continue(vlm_profile, image_profile, selected_run, user_feedback, extra, locale):
        selected = (selected_run or "").strip()
        if not selected:
            return (
                ctx.t("error.run_id_required"),
                "",
                None,
                [],
                ctx.t("studio.status_error"),
                gr.update(open=False),
            )
        options = default_run_options(
            ctx,
            vlm_profile_id=vlm_profile,
            image_profile_id=image_profile,
        )
        try:
            required_roles = roles_for_saved_run(options.output_dir, selected)
            settings = ctx.resolve_settings(options, required_roles)
            log, image, iterations_gallery, error = run_continue(
                settings,
                options.output_dir,
                selected,
                user_feedback or "",
                optional_int(extra),
                verbose_logging=False,
                locale=locale,
            )
            return (
                "",
                log,
                None if error else image,
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
                [],
                ctx.t("studio.status_error"),
                gr.update(open=True),
            )

    _bind_busy(
        gr,
        run,
        status,
        log_panel,
        ctx,
        do_continue,
        [
            header.vlm_profile,
            header.image_profile,
            run_id,
            feedback,
            extra_iterations,
            header.locale,
        ],
        [validation, progress, result, gallery, status, log_panel],
    )
    return ContinuePage(run_id, run)
