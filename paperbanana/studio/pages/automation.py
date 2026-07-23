"""Batch, paper-orchestration, and parameter-sweep workspaces."""

from __future__ import annotations

from dataclasses import dataclass

from paperbanana.connections.models import ConnectionRole
from paperbanana.guidelines.venues import list_venues
from paperbanana.i18n import get_translator, localize_error
from paperbanana.studio.components.options import (
    create_generation_options,
    make_run_options,
    option_inputs,
)
from paperbanana.studio.components.shell import HeaderComponents
from paperbanana.studio.connections_ui import resolve_image_options
from paperbanana.studio.context import StudioContext, optional_int, optional_upload_path
from paperbanana.studio.models import roles_for_batch_type
from paperbanana.studio.runner import (
    ASPECT_RATIO_CHOICES,
    run_batch,
    run_orchestration,
    run_plot_batch,
    run_sweep,
)


@dataclass(frozen=True)
class OrchestratePage:
    run_button: object
    plan_tab: object
    package_tab: object
    log_tab: object


def _run_button(gr, ctx: StudioContext, label: str, elem_id: str):
    return gr.Button(
        label,
        variant="primary",
        interactive=ctx.has_active_connections((ConnectionRole.VLM, ConnectionRole.IMAGE)),
        elem_id=elem_id,
        elem_classes="primary-action",
    )


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


def _initial_image_options(ctx: StudioContext):
    config = ctx.manager.load()
    return resolve_image_options(
        ctx.manager,
        config.active_image_profile_id,
        config.last_aspect_ratio,
        config.last_output_resolution,
        ctx.t,
    )


def build_batch_page(gr, ctx: StudioContext, header: HeaderComponents):
    initial = _initial_image_options(ctx)
    with gr.Row(elem_id="batch-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_id="batch-input-panel", elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                mode = gr.Radio(
                    label=ctx.t("field.batch_type"),
                    choices=[
                        (ctx.t("choice.methodology"), "methodology"),
                        (ctx.t("choice.statistical_plot"), "statistical_plot"),
                    ],
                    value="methodology",
                    elem_id="batch-type",
                    elem_classes="segmented-control",
                )
                manifest = gr.File(
                    label=ctx.t("field.manifest"),
                    file_types=[".yaml", ".yml", ".json"],
                    height=132,
                    elem_id="batch-manifest",
                    elem_classes="compact-file-upload",
                )
                default_ratio = gr.Dropdown(
                    label=ctx.t("field.default_plot_ratio"),
                    choices=[
                        (ctx.t("choice.default"), "default"),
                        *ASPECT_RATIO_CHOICES[1:],
                    ],
                    value="default",
                )
                options = create_generation_options(
                    gr,
                    ctx,
                    prefix="batch",
                    resolution_choices=[(item.upper(), item) for item in initial.resolutions],
                    resolution_value=initial.selected_resolution,
                )
                with gr.Accordion(ctx.t("studio.recovery_settings"), open=False):
                    resume = gr.Textbox(
                        label=ctx.t("field.resume_batch"),
                        placeholder=ctx.t("placeholder.resume_batch"),
                    )
                    retry_failed = gr.Checkbox(label=ctx.t("field.retry_failed"), value=False)
                    with gr.Row(elem_classes="compact-control-row"):
                        max_retries = gr.Number(
                            label=ctx.t("field.max_retries_item"), value=0, precision=0
                        )
                        concurrency = gr.Number(
                            label=ctx.t("field.concurrency"), value=1, precision=0
                        )
                validation = gr.Markdown("", elem_id="batch-validation", elem_classes="validation")
            run = _run_button(gr, ctx, ctx.t("button.batch"), "batch-run")
        with gr.Column(elem_id="batch-result-panel", elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('field.batch_output')}")
                status = gr.Markdown(ctx.t("studio.status_ready"), elem_classes="run-status")
            output = gr.Textbox(
                label=ctx.t("field.batch_output"),
                lines=1,
                placeholder=ctx.t("empty.output_path"),
                elem_classes="result-path-output",
            )
            with gr.Accordion(ctx.t("field.batch_log"), open=False) as log_panel:
                log = gr.Textbox(lines=24, show_label=False, elem_classes="progress-log")

    def do_batch(
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
        batch_mode,
        upload,
        ratio,
        resume_ref,
        retry,
        retry_count,
        workers,
        locale,
    ):
        path = optional_upload_path(upload)
        if not path:
            return (
                ctx.t("error.manifest_required"),
                "",
                "",
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
            settings = ctx.resolve_settings(run_options, roles_for_batch_type(batch_mode))
            common = {
                "resume_batch": (resume_ref or "").strip() or None,
                "retry_failed": bool(retry),
                "max_retries": max(0, int(retry_count or 0)),
                "concurrency": max(1, int(workers or 1)),
                "verbose_logging": False,
                "locale": locale,
            }
            if batch_mode == "statistical_plot":
                progress, path_out = run_plot_batch(
                    settings, path, default_aspect_ratio_label=ratio, **common
                )
            else:
                progress, path_out = run_batch(settings, path, **common)
            return (
                "",
                progress,
                path_out,
                ctx.t("studio.status_complete"),
                gr.update(open=False),
            )
        except Exception as exc:
            message = localize_error(exc, get_translator(locale))
            return message, message, "", ctx.t("studio.status_error"), gr.update(open=True)

    _bind_busy(
        gr,
        run,
        status,
        log_panel,
        ctx,
        do_batch,
        [
            header.vlm_profile,
            header.image_profile,
            *option_inputs(options),
            mode,
            manifest,
            default_ratio,
            resume,
            retry_failed,
            max_retries,
            concurrency,
            header.locale,
        ],
        [validation, log, output, status, log_panel],
    )
    if options.resolution is not None:
        mode.change(
            lambda value: (
                gr.update(interactive=value != "statistical_plot"),
                gr.update(visible=value != "statistical_plot"),
            ),
            inputs=[mode],
            outputs=[header.image_profile, options.resolution],
            queue=False,
        )
    return mode, run


def build_orchestrate_page(gr, ctx: StudioContext, header: HeaderComponents):
    initial = _initial_image_options(ctx)
    venues = sorted(list_venues()) + ["custom"]
    with gr.Row(elem_id="orchestrate-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_id="orchestrate-input-panel", elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                paper = gr.File(
                    label=ctx.t("field.paper_source"),
                    file_types=[".txt", ".md", ".pdf"],
                    height=132,
                    elem_classes="compact-file-upload",
                )
                data_dir = gr.Textbox(
                    label=ctx.t("field.data_directory"),
                    placeholder=ctx.t("placeholder.data_directory"),
                )
                pdf_pages = gr.Textbox(
                    label=ctx.t("field.pdf_pages"), placeholder=ctx.t("placeholder.pdf_pages")
                )
                with gr.Row(elem_classes="compact-control-row"):
                    max_method = gr.Number(
                        label=ctx.t("field.max_method_figures"),
                        value=4,
                        precision=0,
                        minimum=1,
                    )
                    max_plot = gr.Number(
                        label=ctx.t("field.max_plot_figures"),
                        value=4,
                        precision=0,
                        minimum=0,
                    )
                venue = gr.Dropdown(label=ctx.t("field.venue"), choices=venues, value="neurips")
                options = create_generation_options(
                    gr,
                    ctx,
                    prefix="orchestrate",
                    resolution_choices=[(item.upper(), item) for item in initial.resolutions],
                    resolution_value=initial.selected_resolution,
                )
                dry_run = gr.Checkbox(label=ctx.t("field.dry_run"), value=False)
                with gr.Accordion(ctx.t("studio.recovery_settings"), open=False):
                    resume = gr.Textbox(
                        label=ctx.t("field.resume_orchestration"),
                        placeholder=ctx.t("placeholder.resume_orchestration"),
                    )
                    retry = gr.Checkbox(label=ctx.t("field.retry_failed_tasks"), value=False)
                    with gr.Row():
                        max_retries = gr.Number(
                            label=ctx.t("field.max_retries_task"), value=0, precision=0
                        )
                        concurrency = gr.Number(
                            label=ctx.t("field.concurrency"), value=1, precision=0
                        )
                validation = gr.Markdown(
                    "", elem_id="orchestrate-validation", elem_classes="validation"
                )
            run = _run_button(gr, ctx, ctx.t("button.orchestrate"), "orchestrate-run")
        with gr.Column(elem_id="orchestrate-result-panel", elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('field.figure_package')}")
                status = gr.Markdown(ctx.t("studio.status_ready"), elem_classes="run-status")
            output_dir = gr.Textbox(
                label=ctx.t("field.orchestration_directory"),
                placeholder=ctx.t("empty.output_path"),
                elem_classes="result-path-output",
            )
            with gr.Tabs():
                with gr.Tab(ctx.t("field.orchestration_plan")) as plan_tab:
                    plan = gr.Textbox(
                        lines=12,
                        show_label=False,
                        placeholder=ctx.t("empty.orchestration_preview"),
                        elem_classes="result-text-preview",
                    )
                with gr.Tab(ctx.t("field.figure_package")) as package_tab:
                    package = gr.Textbox(
                        lines=12,
                        show_label=False,
                        placeholder=ctx.t("empty.orchestration_preview"),
                        elem_classes="result-text-preview",
                    )
                with gr.Tab(ctx.t("field.orchestration_log")) as orchestration_log_tab:
                    with gr.Accordion(ctx.t("field.log"), open=False) as log_panel:
                        log = gr.Textbox(lines=16, show_label=False, elem_classes="progress-log")

    def do_orchestrate(
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
        paper_upload,
        data_directory,
        page_spec,
        max_method_figures,
        max_plot_figures,
        selected_venue,
        is_dry_run,
        resume_ref,
        retry_failed,
        retry_count,
        workers,
        locale,
    ):
        if not optional_upload_path(paper_upload) and not (resume_ref or "").strip():
            message = ctx.t("error.paper_or_resume_required")
            return message, message, "", "", "", ctx.t("studio.status_error"), gr.update(open=False)
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
            progress, directory, plan_text, package_text = run_orchestration(
                settings,
                paper_file_path=optional_upload_path(paper_upload),
                resume_orchestrate=(resume_ref or "").strip() or None,
                data_dir=(data_directory or "").strip() or None,
                max_method_figures=int(max_method_figures or 4),
                max_plot_figures=int(max_plot_figures or 4),
                pdf_pages=(page_spec or "").strip() or None,
                dry_run=bool(is_dry_run),
                venue=str(selected_venue or "neurips"),
                retry_failed=bool(retry_failed),
                max_retries=max(0, int(retry_count or 0)),
                concurrency=max(1, int(workers or 1)),
                config_path=run_options.config_path,
                verbose_logging=False,
                locale=locale,
            )
            return (
                "",
                progress,
                directory,
                plan_text,
                package_text,
                ctx.t("studio.status_complete"),
                gr.update(open=False),
            )
        except Exception as exc:
            message = localize_error(exc, get_translator(locale))
            return message, message, "", "", "", ctx.t("studio.status_error"), gr.update(open=True)

    _bind_busy(
        gr,
        run,
        status,
        log_panel,
        ctx,
        do_orchestrate,
        [
            header.vlm_profile,
            header.image_profile,
            *option_inputs(options),
            paper,
            data_dir,
            pdf_pages,
            max_method,
            max_plot,
            venue,
            dry_run,
            resume,
            retry,
            max_retries,
            concurrency,
            header.locale,
        ],
        [validation, log, output_dir, plan, package, status, log_panel],
    )
    return OrchestratePage(run, plan_tab, package_tab, orchestration_log_tab)


def build_sweep_page(gr, ctx: StudioContext, header: HeaderComponents):
    initial = _initial_image_options(ctx)
    with gr.Row(elem_id="sweep-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_id="sweep-input-panel", elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                source = gr.File(
                    label=ctx.t("field.methodology_source"),
                    file_types=[".txt", ".md", ".pdf"],
                    height=132,
                    elem_classes="compact-file-upload",
                )
                caption = gr.Textbox(label=ctx.t("field.caption"), lines=2)
                pdf_pages = gr.Textbox(
                    label=ctx.t("field.pdf_pages"),
                    placeholder=ctx.t("placeholder.sweep_pdf_pages"),
                )
                iterations_axis = gr.Textbox(
                    label=ctx.t("field.iteration_axis"),
                    placeholder=ctx.t("placeholder.iterations"),
                )
                optimize_axis = gr.Textbox(
                    label=ctx.t("field.optimize_axis"),
                    placeholder=ctx.t("placeholder.boolean_axis"),
                )
                auto_axis = gr.Textbox(
                    label=ctx.t("field.auto_refine_axis"),
                    placeholder=ctx.t("placeholder.boolean_axis"),
                )
                options = create_generation_options(
                    gr,
                    ctx,
                    prefix="sweep",
                    resolution_choices=[(item.upper(), item) for item in initial.resolutions],
                    resolution_value=initial.selected_resolution,
                )
                with gr.Row(elem_classes="compact-control-row"):
                    max_variants = gr.Number(
                        label=ctx.t("field.max_variants"), value=None, precision=0
                    )
                    dry_run = gr.Checkbox(label=ctx.t("field.dry_run_plan"), value=False)
                validation = gr.Markdown("", elem_id="sweep-validation", elem_classes="validation")
            run = _run_button(gr, ctx, ctx.t("button.sweep"), "sweep-run")
        with gr.Column(elem_id="sweep-result-panel", elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('field.sweep_report')}")
                status = gr.Markdown(ctx.t("studio.status_ready"), elem_classes="run-status")
            output = gr.Textbox(
                label=ctx.t("field.sweep_output"),
                placeholder=ctx.t("empty.output_path"),
                elem_classes="result-path-output",
            )
            report = gr.Textbox(
                label=ctx.t("field.sweep_report"),
                placeholder=ctx.t("empty.output_path"),
                elem_classes="result-path-output",
            )
            with gr.Accordion(ctx.t("field.sweep_log"), open=False) as log_panel:
                log = gr.Textbox(lines=22, show_label=False, elem_classes="progress-log")

    def do_sweep(
        vlm_profile,
        image_profile,
        output_format,
        resolution,
        base_iterations,
        base_auto_refine,
        max_iterations,
        optimize_inputs,
        save_prompts,
        seed,
        upload,
        figure_caption,
        pages,
        iter_axis,
        opt_axis,
        refine_axis,
        limit,
        is_dry,
        locale,
    ):
        path = optional_upload_path(upload)
        if not path:
            message = ctx.t("error.methodology_source_required")
            return message, message, "", "", ctx.t("studio.status_error"), gr.update(open=False)
        try:
            run_options = make_run_options(
                ctx,
                vlm_profile_id=vlm_profile,
                image_profile_id=image_profile,
                output_format=output_format,
                output_resolution=resolution,
                iterations=base_iterations,
                auto_refine=base_auto_refine,
                max_iterations=max_iterations,
                optimize_inputs=optimize_inputs,
                save_prompts=save_prompts,
                seed=seed,
            )
            settings = ctx.resolve_settings(run_options, (ConnectionRole.VLM, ConnectionRole.IMAGE))
            progress, output_path, report_path = run_sweep(
                settings,
                input_path=path,
                caption=figure_caption or "",
                pdf_pages=(pages or "").strip() or None,
                iterations=iter_axis or "",
                optimize_modes=opt_axis or "",
                auto_modes=refine_axis or "",
                max_variants=optional_int(limit),
                dry_run=bool(is_dry),
                verbose_logging=False,
                locale=locale,
            )
            return (
                "",
                progress,
                output_path,
                report_path,
                ctx.t("studio.status_complete"),
                gr.update(open=False),
            )
        except Exception as exc:
            message = localize_error(exc, get_translator(locale))
            return message, message, "", "", ctx.t("studio.status_error"), gr.update(open=True)

    _bind_busy(
        gr,
        run,
        status,
        log_panel,
        ctx,
        do_sweep,
        [
            header.vlm_profile,
            header.image_profile,
            *option_inputs(options),
            source,
            caption,
            pdf_pages,
            iterations_axis,
            optimize_axis,
            auto_axis,
            max_variants,
            dry_run,
            header.locale,
        ],
        [validation, log, output, report, status, log_panel],
    )
    return run
