"""Connection management and persisted Studio defaults."""

from __future__ import annotations

from dataclasses import dataclass

from paperbanana.connections.models import ConnectionRole
from paperbanana.studio.components.shell import HeaderComponents
from paperbanana.studio.connections_ui import ConnectionEditorComponents, build_connection_editor
from paperbanana.studio.context import StudioContext


@dataclass(frozen=True)
class SettingsPage:
    vlm_editor: ConnectionEditorComponents
    image_editor: ConnectionEditorComponents
    vlm_tab: object
    image_tab: object
    general_tab: object
    locale: object


def build_settings_page(gr, ctx: StudioContext, header: HeaderComponents) -> SettingsPage:
    with gr.Tabs(elem_id="connection-role-tabs"):
        with gr.Tab(ctx.t("connection.vlm"), id="settings-vlm") as vlm_tab:
            vlm_editor = build_connection_editor(
                gr,
                ctx.manager,
                ConnectionRole.VLM,
                ctx.t,
                header.vlm_profile,
                header.locale,
            )
        with gr.Tab(ctx.t("connection.image"), id="settings-image") as image_tab:
            image_editor = build_connection_editor(
                gr,
                ctx.manager,
                ConnectionRole.IMAGE,
                ctx.t,
                header.image_profile,
                header.locale,
            )
        with gr.Tab(ctx.t("settings.general"), id="settings-general") as general_tab:
            config = ctx.manager.load()
            with gr.Column(elem_classes="settings-general-panel"):
                gr.Markdown(f"## {ctx.t('settings.locale')}", elem_classes="section-heading")
                with gr.Row(elem_classes="locale-settings-row"):
                    locale = gr.Radio(
                        choices=[("中文", "zh-CN"), ("English", "en")],
                        value=config.locale,
                        label=ctx.t("settings.locale"),
                        show_label=False,
                        elem_id="studio-locale-switch",
                        elem_classes=["locale-switch", "segmented-control"],
                    )
                gr.Markdown(
                    f"## {ctx.t('studio.runtime_heading')}",
                    elem_classes="section-heading runtime-heading",
                )
                gr.Markdown(ctx.t("studio.runtime_help"), elem_classes="page-intro")
                with gr.Row(elem_classes="runtime-settings-row"):
                    output_dir = gr.Textbox(
                        label=ctx.t("settings.output_dir"),
                        value=config.studio_output_dir or ctx.default_output_dir,
                        info=ctx.t("settings.output_dir_help"),
                        elem_id="runtime-output-dir",
                    )
                    config_path = gr.Textbox(
                        label=ctx.t("settings.config_yaml"),
                        value=config.studio_config_path or ctx.default_config_path,
                        placeholder="configs/config.yaml",
                        info=ctx.t("settings.config_yaml_help"),
                        elem_id="runtime-config-path",
                    )
                with gr.Row(elem_classes="runtime-save-row"):
                    save_defaults = gr.Button(
                        ctx.t("settings.save_defaults"),
                        variant="primary",
                        elem_id="runtime-save-defaults",
                    )
                    defaults_status = gr.Markdown("", elem_id="runtime-defaults-status")

    def save_runtime_defaults(output_value, config_value):
        output = (output_value or "").strip()
        if not output:
            return ctx.t("error.output_dir_required")
        ctx.manager.save_studio_defaults(
            output_dir=output,
            config_path=(config_value or "").strip() or None,
        )
        return ctx.t("settings.defaults_saved")

    save_defaults.click(
        save_runtime_defaults,
        inputs=[output_dir, config_path],
        outputs=[defaults_status],
        queue=False,
    )
    return SettingsPage(vlm_editor, image_editor, vlm_tab, image_tab, general_tab, locale)
