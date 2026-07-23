"""Multi-panel composition and run-history tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperbanana.i18n import get_translator, localize_error
from paperbanana.studio import runs as runs_mod
from paperbanana.studio.components.results import create_result_image
from paperbanana.studio.components.shell import HeaderComponents
from paperbanana.studio.context import StudioContext, optional_upload_path
from paperbanana.studio.runner import run_composite


@dataclass(frozen=True)
class RunsPage:
    selected_run: Any
    continue_button: Any
    browse_tab: Any
    compare_tab: Any
    metadata_tab: Any
    run_input_tab: Any


def _studio_output_dir(ctx: StudioContext) -> str:
    return ctx.manager.load().studio_output_dir or ctx.default_output_dir


def build_composite_page(gr, ctx: StudioContext, header: HeaderComponents) -> None:
    with gr.Row(elem_id="composite-workbench", elem_classes="workflow-workbench"):
        with gr.Column(elem_classes="workflow-input-panel"):
            with gr.Column(elem_classes="workflow-input-scroll"):
                files = gr.File(
                    label=ctx.t("field.panel_images"),
                    file_count="multiple",
                    file_types=[".png", ".jpg", ".jpeg", ".webp"],
                    height=150,
                    elem_classes="compact-file-upload",
                )
                with gr.Row(elem_classes="compact-control-row"):
                    layout = gr.Dropdown(
                        label=ctx.t("field.layout"),
                        choices=["auto", "1x2", "1x3", "1x4", "2x2", "2x3", "3x3"],
                        value="auto",
                        allow_custom_value=True,
                        scale=1,
                        min_width=0,
                        elem_id="composite-layout",
                    )
                    label_position = gr.Radio(
                        label=ctx.t("field.label_position"),
                        choices=[
                            (ctx.t("choice.bottom"), "bottom"),
                            (ctx.t("choice.top"), "top"),
                        ],
                        value="bottom",
                        scale=1,
                        min_width=0,
                        elem_id="composite-label-position",
                        elem_classes="segmented-control",
                    )
                labels = gr.Textbox(
                    label=ctx.t("field.labels"), placeholder=ctx.t("placeholder.labels")
                )
                with gr.Row(elem_classes="compact-control-row"):
                    spacing = gr.Number(label=ctx.t("field.spacing"), value=20, precision=0)
                    font_size = gr.Number(
                        label=ctx.t("field.label_font_size"), value=32, precision=0
                    )
                filename = gr.Textbox(label=ctx.t("field.output_filename"), value="composite.png")
            run = gr.Button(
                ctx.t("button.composite"),
                variant="primary",
                elem_id="composite-run",
                elem_classes="primary-action",
            )
        with gr.Column(elem_classes="workflow-result-panel"):
            with gr.Row(elem_classes="result-heading"):
                gr.Markdown(f"### {ctx.t('field.composite_output')}")
                status = gr.Markdown(ctx.t("studio.status_ready"), elem_classes="run-status")
            result = create_result_image(
                gr,
                label=ctx.t("field.composite_output"),
                empty_message=ctx.t("empty.composite_result"),
                elem_id="composite-result",
            )
            log = gr.Textbox(label=ctx.t("field.log"), lines=4, elem_classes="progress-log")

    def do_composite(
        uploads,
        selected_layout,
        panel_labels,
        panel_spacing,
        position,
        label_size,
        output_filename,
        locale,
    ):
        paths = [path for item in (uploads or []) if (path := optional_upload_path(item))]
        try:
            progress, output_path = run_composite(
                paths,
                output_dir=_studio_output_dir(ctx),
                layout=str(selected_layout or "auto"),
                labels=panel_labels or "",
                spacing=int(panel_spacing) if panel_spacing is not None else 20,
                label_position=str(position or "bottom"),
                label_font_size=int(label_size) if label_size is not None else 32,
                output_filename=output_filename or "composite.png",
                locale=locale,
            )
            return progress, output_path, ctx.t("studio.status_complete")
        except Exception as exc:
            return (
                localize_error(exc, get_translator(locale)),
                None,
                ctx.t("studio.status_error"),
            )

    started = run.click(
        lambda: (gr.update(interactive=False), ctx.t("studio.status_running")),
        outputs=[run, status],
        queue=False,
    )
    completed = started.then(
        do_composite,
        inputs=[
            files,
            layout,
            labels,
            spacing,
            label_position,
            font_size,
            filename,
            header.locale,
        ],
        outputs=[log, result, status],
    )
    completed.then(lambda: gr.update(interactive=True), outputs=[run], queue=False)


def _compare_details(data: dict[str, Any]) -> str:
    keys = [
        "run_id",
        "diagram_type",
        "caption",
        "aspect_ratio",
        "vlm_provider",
        "vlm_model",
        "image_provider",
        "image_model",
        "output_format",
        "refinement_iterations",
        "auto_refine",
        "max_iterations",
        "seed",
        "duration_seconds",
        "total_cost_usd",
    ]
    return "\n".join(f"{key}: {data.get(key)}" for key in keys)


def build_runs_page(gr, ctx: StudioContext, header: HeaderComponents) -> RunsPage:
    with gr.Tabs(elem_id="runs-mode-tabs", elem_classes="workspace-tabs"):
        with gr.Tab(ctx.t("studio.runs_browse")) as browse_tab:
            with gr.Row(elem_id="runs-workbench", elem_classes="runs-workbench"):
                with gr.Column(elem_id="runs-browser", elem_classes="runs-browser"):
                    refresh = gr.Button(
                        ctx.t("button.refresh"),
                        variant="secondary",
                        elem_id="runs-refresh",
                        elem_classes="secondary-action",
                    )
                    run_pick = gr.Dropdown(
                        label=ctx.t("field.runs"),
                        choices=[],
                        allow_custom_value=True,
                        elem_id="runs-run-selector",
                    )
                    continue_selected = gr.Button(
                        ctx.t("button.continue_selected"),
                        variant="secondary",
                        elem_id="runs-continue-selected",
                        elem_classes="secondary-action",
                    )
                    batch_pick = gr.Dropdown(
                        label=ctx.t("field.batches"),
                        choices=[],
                        allow_custom_value=True,
                        elem_id="runs-batch-selector",
                    )
                    batch_report = gr.Textbox(
                        label=ctx.t("field.batch_report_preview"),
                        lines=7,
                        elem_id="runs-batch-report",
                    )
                with gr.Column(elem_id="runs-detail", elem_classes="runs-detail"):
                    selected_image = create_result_image(
                        gr,
                        label=ctx.t("field.selected_run_output"),
                        empty_message=ctx.t("empty.selected_run"),
                        height=270,
                        elem_id="runs-selected-image",
                        image_classes="history-result",
                        stage_classes="result-stage history-result-stage",
                    )
                    iterations = gr.Gallery(
                        label=ctx.t("field.iteration_thumbnails"),
                        columns=5,
                        height=116,
                        elem_classes="history-iterations empty-result-surface",
                    )
                    with gr.Tabs(elem_classes="detail-tabs"):
                        with gr.Tab(ctx.t("field.metadata_preview")) as metadata_tab:
                            metadata = gr.Textbox(lines=6, show_label=False)
                        with gr.Tab(ctx.t("field.run_input_preview")) as run_input_tab:
                            run_input = gr.Textbox(lines=6, show_label=False)

        with gr.Tab(ctx.t("studio.runs_compare")) as compare_tab:
            with gr.Column(elem_classes="runs-compare-workspace"):
                with gr.Row(elem_classes="compare-selectors"):
                    compare_left = gr.Dropdown(
                        label=ctx.t("field.left_run"),
                        choices=[],
                        allow_custom_value=True,
                        min_width=0,
                    )
                    compare_right = gr.Dropdown(
                        label=ctx.t("field.right_run"),
                        choices=[],
                        allow_custom_value=True,
                        min_width=0,
                    )
                    compare = gr.Button(
                        ctx.t("button.compare"),
                        variant="primary",
                        elem_id="runs-compare",
                    )
                difference = gr.Markdown(
                    ctx.t("empty.compare_result"),
                    elem_classes="compare-difference empty-result-copy",
                )
                with gr.Row(elem_classes="compare-results"):
                    with gr.Column():
                        left_image = gr.Image(
                            label=ctx.t("field.left_output"),
                            type="filepath",
                            height=250,
                            placeholder=ctx.t("empty.compare_result"),
                        )
                        left_details = gr.Textbox(
                            label=ctx.t("field.left_details"),
                            lines=7,
                        )
                    with gr.Column():
                        right_image = gr.Image(
                            label=ctx.t("field.right_output"),
                            type="filepath",
                            height=250,
                            placeholder=ctx.t("empty.compare_result"),
                        )
                        right_details = gr.Textbox(
                            label=ctx.t("field.right_details"),
                            lines=7,
                        )

    def refresh_runs():
        root = _studio_output_dir(ctx)
        runs = runs_mod.list_run_ids(root)
        batches = runs_mod.list_batch_ids(root)
        left_default = runs[-2] if len(runs) >= 2 else (runs[-1] if runs else None)
        return (
            gr.update(choices=runs, value=runs[-1] if runs else None),
            gr.update(choices=batches, value=batches[-1] if batches else None),
            gr.update(choices=runs, value=left_default),
            gr.update(choices=runs, value=runs[-1] if runs else None),
        )

    def show_run(run_id: str | None):
        if not run_id:
            return None, "", "", []
        summary = runs_mod.load_run_summary(_studio_output_dir(ctx), run_id)
        gallery = [(path, Path(path).name) for path in summary.get("iteration_images") or []]
        return (
            summary.get("final_image") or None,
            summary.get("metadata_preview") or "",
            summary.get("run_input_preview") or "",
            gallery,
        )

    def show_batch(batch_id: str | None):
        if not batch_id:
            return ""
        summary = runs_mod.load_batch_summary(_studio_output_dir(ctx), batch_id)
        return summary.get("report_preview") or ""

    def show_compare(left_id: str | None, right_id: str | None, locale: str):
        translator = get_translator(locale)
        if not left_id or not right_id:
            return None, None, translator("compare.select_both"), "", ""
        comparison = runs_mod.compare_runs(_studio_output_dir(ctx), left_id, right_id)
        if comparison.get("error"):
            return None, None, str(comparison["error"]), "", ""
        left = comparison.get("left") or {}
        right = comparison.get("right") or {}
        diffs = comparison.get("diffs") or []
        if not diffs:
            diff_markdown = translator("compare.no_differences")
        else:
            rows = [translator("compare.differences"), ""]
            rows.extend(
                translator(
                    "compare.row",
                    field=item.get("field"),
                    left=item.get("left"),
                    right=item.get("right"),
                )
                for item in diffs
            )
            diff_markdown = "\n".join(rows)
        return (
            left.get("final_image"),
            right.get("final_image"),
            diff_markdown,
            _compare_details(left),
            _compare_details(right),
        )

    refresh.click(
        refresh_runs,
        outputs=[run_pick, batch_pick, compare_left, compare_right],
    )
    run_pick.change(
        show_run,
        inputs=[run_pick],
        outputs=[selected_image, metadata, run_input, iterations],
    )
    batch_pick.change(show_batch, inputs=[batch_pick], outputs=[batch_report])
    compare.click(
        show_compare,
        inputs=[compare_left, compare_right, header.locale],
        outputs=[left_image, right_image, difference, left_details, right_details],
    )
    return RunsPage(
        run_pick,
        continue_selected,
        browse_tab,
        compare_tab,
        metadata_tab,
        run_input_tab,
    )
