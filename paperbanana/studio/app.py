"""PaperBanana-CN desktop Studio application."""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from threading import Thread
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from paperbanana.connections.manager import ConnectionManager
from paperbanana.connections.models import ConnectionRole
from paperbanana.i18n import SUPPORTED_LOCALES, get_catalogs, get_translator
from paperbanana.studio.branding import (
    BRAND_LOGO_PATH,
    STUDIO_ASSET_DIR,
    STUDIO_ASSET_MOUNT,
)
from paperbanana.studio.components.shell import (
    build_header,
    build_sidebar,
    navigation_buttons_in_order,
    navigation_updates,
    refresh_active_profiles,
)
from paperbanana.studio.connections_ui import refresh_connection_editor
from paperbanana.studio.context import StudioContext
from paperbanana.studio.language import locale_ready_js, locale_switch_js
from paperbanana.studio.models import (
    WORKFLOW_BY_KEY,
    WORKFLOW_SPECS,
    roles_for_batch_type,
    roles_for_saved_run,
)
from paperbanana.studio.pages.automation import (
    build_batch_page,
    build_orchestrate_page,
    build_sweep_page,
)
from paperbanana.studio.pages.generate import (
    bind_image_options,
    build_diagram_page,
    build_plot_page,
)
from paperbanana.studio.pages.improve import build_continue_page, build_evaluate_page
from paperbanana.studio.pages.settings import build_settings_page
from paperbanana.studio.pages.tools import build_composite_page, build_runs_page


def _dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _styles() -> str:
    return Path(__file__).with_name("styles.css").read_text(encoding="utf-8")


def _light_theme(gr):
    theme = gr.themes.Base(
        primary_hue="emerald",
        secondary_hue="amber",
        neutral_hue="gray",
        font=["Inter", "Noto Sans SC", "Microsoft YaHei", "sans-serif"],
    )
    return theme.set(
        body_background_fill="#EEF1F0",
        body_background_fill_dark="#EEF1F0",
        body_text_color="#18211E",
        body_text_color_dark="#18211E",
        body_text_color_subdued="#34423D",
        body_text_color_subdued_dark="#34423D",
        background_fill_primary="#FFFFFF",
        background_fill_primary_dark="#FFFFFF",
        background_fill_secondary="#F6F8F7",
        background_fill_secondary_dark="#F6F8F7",
        border_color_primary="#CBD4CF",
        border_color_primary_dark="#CBD4CF",
        block_background_fill="#FFFFFF",
        block_background_fill_dark="#FFFFFF",
        block_border_color="#CBD4CF",
        block_border_color_dark="#CBD4CF",
        block_label_background_fill="#FFFFFF",
        block_label_background_fill_dark="#FFFFFF",
        block_label_text_color="#34423D",
        block_label_text_color_dark="#34423D",
        block_label_text_size="13px",
        block_label_text_weight="600",
        input_background_fill="#FFFFFF",
        input_background_fill_dark="#FFFFFF",
        input_background_fill_focus="#FFFFFF",
        input_background_fill_focus_dark="#FFFFFF",
        input_border_color="#AEBBB4",
        input_border_color_dark="#AEBBB4",
        input_border_color_focus="#147862",
        input_border_color_focus_dark="#147862",
        input_placeholder_color="#43514C",
        input_placeholder_color_dark="#43514C",
        button_primary_background_fill="#147862",
        button_primary_background_fill_dark="#147862",
        button_primary_background_fill_hover="#0F6653",
        button_primary_background_fill_hover_dark="#0F6653",
        button_primary_text_color="#FFFFFF",
        button_primary_text_color_dark="#FFFFFF",
        button_secondary_background_fill="#FFFFFF",
        button_secondary_background_fill_dark="#FFFFFF",
        button_secondary_text_color="#18211E",
        button_secondary_text_color_dark="#18211E",
        button_secondary_border_color="#AEBBB4",
        button_secondary_border_color_dark="#AEBBB4",
    )


def build_studio_app(
    *,
    default_output_dir: str = "outputs",
    config_path: Optional[str] = None,
    connection_manager: ConnectionManager | None = None,
    locale: str | None = None,
):
    """Construct the single-page bilingual Gradio workbench."""
    import gradio as gr

    _dotenv()
    manager = connection_manager or ConnectionManager()
    config = manager.load()
    selected_locale = locale or config.locale
    if selected_locale not in SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported Studio locale: {selected_locale}")
    i18n = gr.I18n(**get_catalogs())
    ctx = StudioContext(
        manager=manager,
        translator=get_translator(selected_locale),
        frontend_translator=i18n,
        locale=selected_locale,
        default_output_dir=default_output_dir,
        default_config_path=config_path or "",
    )

    with gr.Blocks(
        title="PaperBanana-CN",
        fill_height=True,
        fill_width=True,
    ) as demo:
        with gr.Row(elem_id="studio-shell"):
            with gr.Column(elem_id="studio-nav", scale=0, min_width=224):
                nav_buttons = build_sidebar(gr, ctx)
            with gr.Column(elem_id="studio-main", scale=1):
                header = build_header(gr, ctx)
                with gr.Column(elem_id="studio-content"):
                    with gr.Column(elem_id="studio-workflows"):
                        workflow_pages = {}
                        with gr.Column(
                            visible=True,
                            elem_id="page-diagram",
                            elem_classes="workflow-page",
                        ) as workflow_pages["diagram"]:
                            diagram = build_diagram_page(gr, ctx, header)
                        with gr.Column(
                            visible=False, elem_id="page-plot", elem_classes="workflow-page"
                        ) as workflow_pages["plot"]:
                            plot_action = build_plot_page(gr, ctx, header)
                        with gr.Column(
                            visible=False,
                            elem_id="page-continue",
                            elem_classes="workflow-page",
                        ) as workflow_pages["continue"]:
                            continue_page = build_continue_page(gr, ctx, header)
                        with gr.Column(
                            visible=False,
                            elem_id="page-evaluate",
                            elem_classes="workflow-page",
                        ) as workflow_pages["evaluate"]:
                            evaluate_action = build_evaluate_page(gr, ctx, header)
                        with gr.Column(
                            visible=False,
                            elem_id="page-orchestrate",
                            elem_classes="workflow-page",
                        ) as workflow_pages["orchestrate"]:
                            orchestrate_page = build_orchestrate_page(gr, ctx, header)
                        with gr.Column(
                            visible=False, elem_id="page-batch", elem_classes="workflow-page"
                        ) as workflow_pages["batch"]:
                            batch_mode, batch_action = build_batch_page(gr, ctx, header)
                        with gr.Column(
                            visible=False, elem_id="page-sweep", elem_classes="workflow-page"
                        ) as workflow_pages["sweep"]:
                            sweep_action = build_sweep_page(gr, ctx, header)
                        with gr.Column(
                            visible=False,
                            elem_id="page-composite",
                            elem_classes="workflow-page",
                        ) as workflow_pages["composite"]:
                            build_composite_page(gr, ctx, header)
                        with gr.Column(
                            visible=False, elem_id="page-runs", elem_classes="workflow-page"
                        ) as workflow_pages["runs"]:
                            runs_page = build_runs_page(gr, ctx, header)
                        with gr.Column(
                            visible=False,
                            elem_id="page-settings",
                            elem_classes="workflow-page",
                        ) as workflow_pages["settings"]:
                            settings_page = build_settings_page(gr, ctx, header)

        ordered_buttons = navigation_buttons_in_order(nav_buttons)
        nav_outputs = [
            header.page_title,
            *[workflow_pages[item.key] for item in WORKFLOW_SPECS],
            *ordered_buttons,
        ]
        for page, button in nav_buttons.items():
            button.click(
                lambda selected=page: navigation_updates(gr, ctx, selected),
                outputs=nav_outputs,
                queue=False,
            )

        diagram.configure_button.click(
            lambda: navigation_updates(gr, ctx, "settings"),
            outputs=nav_outputs,
            queue=False,
        )

        def save_locale(selected):
            manager.save_preferences(locale=selected)
            translator = get_translator(selected)
            return (
                selected,
                selected,
                gr.update(label=translator("connection.vlm")),
                gr.update(label=translator("connection.image")),
                gr.update(label=translator("settings.general")),
                gr.update(label=translator("field.orchestration_plan")),
                gr.update(label=translator("field.figure_package")),
                gr.update(label=translator("field.orchestration_log")),
                gr.update(label=translator("studio.runs_browse")),
                gr.update(label=translator("studio.runs_compare")),
                gr.update(label=translator("field.metadata_preview")),
                gr.update(label=translator("field.run_input_preview")),
            )

        locale_outputs = [
            header.locale,
            settings_page.locale,
            settings_page.vlm_tab,
            settings_page.image_tab,
            settings_page.general_tab,
            orchestrate_page.plan_tab,
            orchestrate_page.package_tab,
            orchestrate_page.log_tab,
            runs_page.browse_tab,
            runs_page.compare_tab,
            runs_page.metadata_tab,
            runs_page.run_input_tab,
        ]

        settings_page.locale.input(
            save_locale,
            inputs=[settings_page.locale],
            outputs=locale_outputs,
            js=locale_switch_js(gr, initial=False),
            queue=False,
        )

        guarded_actions = [
            diagram.generate_button,
            plot_action,
            evaluate_action,
            continue_page.run_button,
            orchestrate_page.run_button,
            batch_action,
            sweep_action,
        ]

        def update_connection_gates(vlm_profile_id, image_profile_id, run_id, batch_type):
            selected = {
                ConnectionRole.VLM: vlm_profile_id,
                ConnectionRole.IMAGE: image_profile_id,
            }

            def ready(roles):
                return all(selected[role] for role in roles)

            run_root = manager.load().studio_output_dir or ctx.default_output_dir
            try:
                continue_ready = bool(run_id) and ready(roles_for_saved_run(run_root, run_id))
            except (FileNotFoundError, ValueError):
                continue_ready = False
            action_states = [
                ready(WORKFLOW_BY_KEY["diagram"].required_roles),
                ready(WORKFLOW_BY_KEY["plot"].required_roles),
                ready(WORKFLOW_BY_KEY["evaluate"].required_roles),
                continue_ready,
                ready(WORKFLOW_BY_KEY["orchestrate"].required_roles),
                ready(roles_for_batch_type(batch_type)),
                ready(WORKFLOW_BY_KEY["sweep"].required_roles),
            ]
            return (
                *[gr.update(interactive=value) for value in action_states],
                gr.update(visible=not action_states[0]),
            )

        gate_inputs = [
            header.vlm_profile,
            header.image_profile,
            continue_page.run_id,
            batch_mode,
        ]
        gate_outputs = [*guarded_actions, diagram.connection_gate]
        for selector in gate_inputs:
            selector.change(
                update_connection_gates,
                inputs=gate_inputs,
                outputs=gate_outputs,
                queue=False,
            )
        bind_image_options(gr, ctx, header, diagram)

        runs_page.continue_button.click(
            lambda selected: (*navigation_updates(gr, ctx, "continue"), selected),
            inputs=[runs_page.selected_run],
            outputs=[*nav_outputs, continue_page.run_id],
            queue=False,
        )

        editor_outputs = [
            *settings_page.vlm_editor.load_outputs(),
            *settings_page.image_editor.load_outputs(),
        ]

        def refresh_page_state():
            return (
                *refresh_active_profiles(ctx),
                *refresh_connection_editor(gr, manager, settings_page.vlm_editor, ctx.t),
                *refresh_connection_editor(gr, manager, settings_page.image_editor, ctx.t),
            )

        initial_locale = demo.load(
            save_locale,
            inputs=[settings_page.locale],
            outputs=locale_outputs,
            js=locale_switch_js(gr, initial=True),
            queue=False,
            show_progress="hidden",
        )
        initial_state = initial_locale.then(
            refresh_page_state,
            outputs=[header.vlm_profile, header.image_profile, *editor_outputs],
            queue=False,
            show_progress="hidden",
        )
        initial_gates = initial_state.then(
            update_connection_gates,
            inputs=gate_inputs,
            outputs=gate_outputs,
            queue=False,
            show_progress="hidden",
        )
        initial_gates.then(
            fn=None,
            js=locale_ready_js(),
            queue=False,
            show_progress="hidden",
        )

    demo.paperbanana_css = _styles()
    demo.paperbanana_theme = _light_theme(gr)
    demo.paperbanana_i18n = i18n
    return demo


def build_studio_server_app(
    *,
    default_output_dir: str = "outputs",
    config_path: Optional[str] = None,
    connection_manager: ConnectionManager | None = None,
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    root_path: str | None = None,
):
    """Mount one bilingual Gradio app at the server root."""
    import gradio as gr

    manager = connection_manager or ConnectionManager()
    server = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    server.mount(
        STUDIO_ASSET_MOUNT,
        StaticFiles(directory=STUDIO_ASSET_DIR),
        name="paperbanana-assets",
    )
    blocks = build_studio_app(
        default_output_dir=default_output_dir,
        config_path=config_path,
        connection_manager=manager,
    )
    return gr.mount_gradio_app(
        server,
        blocks.queue(),
        path="/",
        server_name=server_name,
        server_port=server_port,
        root_path=root_path,
        footer_links=[],
        favicon_path=str(BRAND_LOGO_PATH),
        theme=_light_theme(gr),
        css=_styles(),
        i18n=blocks.paperbanana_i18n,
        show_error=True,
    )


def launch_studio(
    *,
    host: str = "127.0.0.1",
    port: int = 7860,
    share: bool = False,
    config_path: Optional[str] = None,
    default_output_dir: str = "outputs",
    root_path: Optional[str] = None,
) -> None:
    """Build and launch the bilingual Studio server."""
    import uvicorn

    server_app = build_studio_server_app(
        default_output_dir=default_output_dir,
        config_path=config_path,
        server_name=host,
        server_port=port,
        root_path=root_path,
    )
    config = uvicorn.Config(
        server_app,
        host=host,
        port=port,
        root_path=root_path or "",
        log_level="info",
    )
    server = uvicorn.Server(config)
    if not share:
        server.run()
        return

    thread = Thread(target=server.run, daemon=True)
    thread.start()
    while thread.is_alive() and not server.started:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("Studio server failed to start")
    from gradio import networking

    share_url = networking.setup_tunnel(
        local_host=host,
        local_port=port,
        share_token=secrets.token_urlsafe(32),
        share_server_address=None,
        share_server_tls_certificate=None,
    )
    print(f"* Running on public URL: {share_url}")
    try:
        while thread.is_alive():
            thread.join(timeout=0.5)
    except KeyboardInterrupt:
        server.should_exit = True
        thread.join(timeout=5)
