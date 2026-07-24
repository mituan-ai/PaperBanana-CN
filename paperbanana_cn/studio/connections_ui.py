"""Gradio connection editors backed by the shared connection manager."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from paperbanana_cn.connections.manager import ConnectionManager
from paperbanana_cn.connections.models import ConnectionProfile, ConnectionRole
from paperbanana_cn.connections.testing import (
    runtime_settings_for_profile,
    sanitize_connection_error,
    test_connection,
    validate_connection,
)
from paperbanana_cn.core.config import OUTPUT_RESOLUTION_VALUES
from paperbanana_cn.core.types import ASPECT_RATIO_VALUES
from paperbanana_cn.i18n import get_translator, localize_error
from paperbanana_cn.providers.registry import ProviderRegistry

VLM_PROVIDERS = ("gemini", "openai", "openrouter", "atlas", "anthropic") + (
    "ollama",
    "openai_local",
    "bedrock",
    "claude_code",
    "litellm",
)
IMAGE_PROVIDERS = ("google_imagen", "openai_imagen", "atlas_imagen") + (
    "openrouter_imagen",
    "bedrock_imagen",
)
IMAGE_SIZE_MODES = ["native_tier", "explicit_pixels", "fixed", "prompt_hint"]


def image_size_mode_choices(t) -> list[tuple[str, str]]:
    return [(t(f"connection.size_mode_{value}"), value) for value in IMAGE_SIZE_MODES]


@dataclass(frozen=True)
class ImageOptionState:
    ratios: list[str]
    resolutions: list[str]
    selected_ratio: str | None
    selected_resolution: str | None
    preview: str


@dataclass(frozen=True)
class ConnectionEditorComponents:
    role: ConnectionRole
    selector: object
    name: object
    provider: object
    base_url: object
    model: object
    timeout: object
    key_status: object
    size_mode: object
    status: object
    api_key: object

    def load_outputs(self) -> list[object]:
        return [
            self.selector,
            self.name,
            self.provider,
            self.base_url,
            self.model,
            self.timeout,
            self.key_status,
            self.size_mode,
            self.status,
            self.api_key,
        ]


def resolve_image_options(
    manager: ConnectionManager,
    profile_id: str | None,
    aspect_ratio: str | None,
    resolution: str | None,
    t,
) -> ImageOptionState:
    """Resolve Studio choices from the selected provider's declared capabilities."""
    if not profile_id:
        return ImageOptionState(
            ratios=list(ASPECT_RATIO_VALUES),
            resolutions=list(OUTPUT_RESOLUTION_VALUES),
            selected_ratio=aspect_ratio,
            selected_resolution=resolution,
            preview=t("size.configure_connection"),
        )
    try:
        profile = manager.load().profile(profile_id, ConnectionRole.IMAGE)
        settings = runtime_settings_for_profile(manager, profile)
        provider = ProviderRegistry.create_image_gen(settings, validate_credentials=False)
    except Exception as exc:
        return ImageOptionState(
            [],
            [],
            None,
            None,
            t("size.capability_error", error=localize_error(exc, t)),
        )

    ratios = [item for item in ASPECT_RATIO_VALUES if item in provider.supported_ratios]
    resolutions = [
        item for item in OUTPUT_RESOLUTION_VALUES if item in provider.supported_resolutions
    ]
    selected_ratio = aspect_ratio if aspect_ratio in ratios else None
    selected_resolution = resolution if resolution in resolutions else None
    if selected_ratio is None or selected_resolution is None:
        preview = t("size.choose_supported")
    else:
        from paperbanana_cn.agents.visualizer import VisualizerAgent

        width, height = VisualizerAgent._ratio_to_dimensions(selected_ratio, selected_resolution)
        request_size = provider.requested_size_label(
            selected_ratio,
            selected_resolution,
            width,
            height,
        )
        preview = t(
            "size.preview",
            provider=provider.name,
            request_size=request_size,
            mode=provider.size_mode.value,
        )
    return ImageOptionState(
        ratios=ratios,
        resolutions=resolutions,
        selected_ratio=selected_ratio,
        selected_resolution=selected_resolution,
        preview=preview,
    )


def profile_choices(manager: ConnectionManager, role: ConnectionRole) -> list[tuple[str, str]]:
    return [
        (profile.name, profile.id) for profile in manager.load().profiles if profile.role == role
    ]


def _active_profile(manager: ConnectionManager, role: ConnectionRole) -> str | None:
    config = manager.load()
    return (
        config.active_vlm_profile_id
        if role == ConnectionRole.VLM
        else config.active_image_profile_id
    )


def _editor_values(manager: ConnectionManager, role: ConnectionRole, profile_id: str | None, t):
    if not profile_id:
        provider = "openai" if role == ConnectionRole.VLM else "google_imagen"
        model = "gpt-5.2" if role == ConnectionRole.VLM else "gemini-3-pro-image-preview"
        return "", provider, "", model, 180, t("connection.key_missing"), None, ""
    profile = manager.load().profile(profile_id, role)
    key_status = (
        t("connection.key_saved") if profile.credential_ref else t("connection.key_missing")
    )
    return (
        profile.name,
        profile.provider,
        profile.base_url or "",
        profile.model,
        profile.timeout_seconds,
        key_status,
        profile.image_size_mode,
        "",
    )


def _profile_from_editor(
    manager,
    role,
    profile_id,
    name,
    provider,
    base_url,
    model,
    timeout,
    size_mode,
) -> ConnectionProfile:
    existing = None
    if profile_id:
        try:
            existing = manager.load().profile(profile_id, role)
        except KeyError:
            pass
    return ConnectionProfile(
        id=existing.id if existing else str(uuid4()),
        name=name,
        role=role,
        provider=provider,
        base_url=base_url or None,
        model=model,
        timeout_seconds=float(timeout),
        credential_ref=existing.credential_ref if existing else None,
        image_size_mode=size_mode if role == ConnectionRole.IMAGE else None,
    )


def build_connection_editor(
    gr, manager, role: ConnectionRole, t, active_selector, locale_selector
) -> ConnectionEditorComponents:
    """Build a master-detail editor; browsing never changes the active connection."""
    role_id = role.value
    selected = _active_profile(manager, role)
    initial = _editor_values(manager, role, selected, t)
    providers = VLM_PROVIDERS if role == ConnectionRole.VLM else IMAGE_PROVIDERS

    with gr.Row(elem_classes=["connection-master-detail", f"connection-editor-{role_id}"]):
        with gr.Column(elem_classes="connection-master", min_width=0):
            profile_pick = gr.Radio(
                label=t("connection.profile"),
                choices=profile_choices(manager, role),
                value=selected,
                elem_id=f"connection-{role_id}-selector",
                elem_classes="connection-list",
            )
            with gr.Row():
                new_button = gr.Button(
                    t("connection.new"),
                    variant="secondary",
                    size="sm",
                    elem_id=f"connection-{role_id}-new",
                )
                copy_button = gr.Button(
                    t("connection.copy"),
                    variant="secondary",
                    size="sm",
                    elem_id=f"connection-{role_id}-copy",
                )
        with gr.Column(elem_classes="connection-detail"):
            name = gr.Textbox(
                label=t("connection.name"),
                value=initial[0],
                elem_id=f"connection-{role_id}-name",
            )
            with gr.Row(elem_classes="compact-control-row"):
                provider = gr.Dropdown(
                    label=t("connection.provider"),
                    choices=providers,
                    value=initial[1],
                    allow_custom_value=True,
                    min_width=0,
                    elem_id=f"connection-{role_id}-provider",
                )
                timeout = gr.Number(
                    label=t("connection.timeout"),
                    value=initial[4],
                    minimum=1,
                    maximum=1800,
                    min_width=0,
                    elem_id=f"connection-{role_id}-timeout",
                )
            base_url = gr.Textbox(
                label=t("connection.base_url"),
                value=initial[2],
                elem_id=f"connection-{role_id}-url",
            )
            model = gr.Textbox(
                label=t("connection.model"),
                value=initial[3],
                elem_id=f"connection-{role_id}-model",
            )
            size_mode = gr.Dropdown(
                label=t("connection.size_mode"),
                choices=image_size_mode_choices(t),
                value=initial[6],
                visible=role == ConnectionRole.IMAGE,
                elem_id=f"connection-{role_id}-size-mode",
            )
            api_key = gr.Textbox(
                label=t("connection.api_key"),
                type="password",
                value="",
                elem_id=f"connection-{role_id}-api-key",
            )
            key_status = gr.Markdown(
                initial[5],
                elem_id=f"connection-{role_id}-key-status",
                elem_classes="credential-status",
            )
            status = gr.Markdown(
                initial[7],
                elem_id=f"connection-{role_id}-status",
                elem_classes="connection-status",
            )
            with gr.Row(elem_classes="connection-actions"):
                save_button = gr.Button(
                    t("connection.save_only"),
                    variant="secondary",
                    elem_id=f"connection-{role_id}-save",
                )
                save_use_button = gr.Button(
                    t("connection.save"),
                    variant="primary",
                    elem_id=f"connection-{role_id}-save-use",
                )
                test_button = gr.Button(
                    t("connection.test")
                    if role == ConnectionRole.VLM
                    else t("connection.test_image"),
                    variant="secondary",
                    elem_id=f"connection-{role_id}-test",
                    elem_classes=(
                        "secondary-action" if role == ConnectionRole.VLM else "paid-action"
                    ),
                )
            with gr.Row(elem_classes="danger-actions"):
                clear_button = gr.Button(
                    t("connection.clear_key"), size="sm", elem_id=f"connection-{role_id}-clear"
                )
                delete_button = gr.Button(
                    t("connection.delete"), size="sm", elem_id=f"connection-{role_id}-delete"
                )

            with gr.Group(
                visible=False, elem_id=f"connection-{role_id}-clear-confirm"
            ) as clear_confirm:
                gr.Markdown(t("connection.clear_key_confirm"))
                with gr.Row():
                    clear_cancel = gr.Button(t("connection.cancel"), size="sm")
                    clear_apply = gr.Button(
                        t("connection.clear_key_apply"), variant="stop", size="sm"
                    )
            with gr.Group(
                visible=False, elem_id=f"connection-{role_id}-delete-confirm"
            ) as delete_confirm:
                gr.Markdown(t("connection.delete_confirm"))
                with gr.Row():
                    delete_cancel = gr.Button(t("connection.cancel"), size="sm")
                    delete_apply = gr.Button(
                        t("connection.delete_apply"), variant="stop", size="sm"
                    )
            with gr.Group(
                visible=False, elem_id=f"connection-{role_id}-paid-confirm"
            ) as paid_confirm:
                gr.Markdown(t("connection.paid_confirm"))
                with gr.Row():
                    paid_cancel = gr.Button(t("connection.cancel"), size="sm")
                    paid_apply = gr.Button(
                        t("connection.paid_apply"),
                        variant="secondary",
                        size="sm",
                        elem_classes="paid-action",
                    )

    editor_outputs = [name, provider, base_url, model, timeout, key_status, size_mode, status]
    profile_pick.input(
        lambda profile_id, locale: _editor_values(
            manager, role, profile_id, get_translator(locale)
        ),
        inputs=[profile_pick, locale_selector],
        outputs=editor_outputs,
    )
    new_button.click(
        lambda locale: (
            None,
            *_editor_values(manager, role, None, get_translator(locale)),
        ),
        inputs=[locale_selector],
        outputs=[profile_pick, *editor_outputs],
    )

    editor_inputs = [
        profile_pick,
        name,
        provider,
        base_url,
        model,
        timeout,
        api_key,
        size_mode,
        locale_selector,
    ]

    def save_profile(activate, profile_id, *values):
        runtime_t = get_translator(values[-1])
        profile = _profile_from_editor(manager, role, profile_id, *values[:5], values[6])
        saved = manager.save_profile(
            profile,
            api_key=values[5],
            make_active=activate,
        )
        stored = saved.profile(profile.id, role)
        credential = (
            runtime_t("connection.key_saved")
            if stored.credential_ref
            else runtime_t("connection.key_missing")
        )
        active_id = _active_profile(manager, role)
        choices = profile_choices(manager, role)
        return (
            gr.update(choices=choices, value=profile.id),
            active_id,
            "",
            credential,
            runtime_t("connection.saved", name=profile.name),
        )

    save_outputs = [profile_pick, active_selector, api_key, key_status, status]
    save_button.click(
        lambda profile_id, *values: save_profile(False, profile_id, *values),
        inputs=editor_inputs,
        outputs=save_outputs,
    )
    save_use_button.click(
        lambda profile_id, *values: save_profile(True, profile_id, *values),
        inputs=editor_inputs,
        outputs=save_outputs,
    )

    def copy_profile(profile_id, locale):
        runtime_t = get_translator(locale)
        if not profile_id:
            return gr.update(), runtime_t("connection.select_first")
        source = manager.load().profile(profile_id, role)
        duplicate = source.model_copy(
            update={
                "id": str(uuid4()),
                "name": f"{source.name} {runtime_t('connection.copy_suffix')}",
            }
        )
        manager.save_profile(duplicate, make_active=False)
        return (
            gr.update(choices=profile_choices(manager, role), value=duplicate.id),
            runtime_t("connection.copied", name=duplicate.name),
        )

    copy_button.click(
        copy_profile,
        inputs=[profile_pick, locale_selector],
        outputs=[profile_pick, status],
    )

    clear_button.click(lambda: gr.update(visible=True), outputs=[clear_confirm], queue=False)
    clear_cancel.click(lambda: gr.update(visible=False), outputs=[clear_confirm], queue=False)

    def clear_credential(profile_id, locale):
        runtime_t = get_translator(locale)
        if not profile_id:
            return (
                gr.update(visible=False),
                runtime_t("connection.select_first"),
                runtime_t("connection.key_missing"),
            )
        profile = manager.load().profile(profile_id, role)
        manager.save_profile(profile, clear_api_key=True, make_active=False)
        return (
            gr.update(visible=False),
            runtime_t("connection.key_cleared"),
            runtime_t("connection.key_missing"),
        )

    clear_apply.click(
        clear_credential,
        inputs=[profile_pick, locale_selector],
        outputs=[clear_confirm, status, key_status],
    )

    delete_button.click(lambda: gr.update(visible=True), outputs=[delete_confirm], queue=False)
    delete_cancel.click(lambda: gr.update(visible=False), outputs=[delete_confirm], queue=False)

    def delete_profile(profile_id, locale):
        runtime_t = get_translator(locale)
        if not profile_id:
            return (
                gr.update(),
                gr.update(),
                gr.update(visible=False),
                runtime_t("connection.select_first"),
            )
        manager.delete_profile(profile_id)
        choices = profile_choices(manager, role)
        return (
            gr.update(choices=choices, value=None),
            _active_profile(manager, role),
            gr.update(visible=False),
            runtime_t("connection.deleted"),
        )

    delete_apply.click(
        delete_profile,
        inputs=[profile_pick, locale_selector],
        outputs=[profile_pick, active_selector, delete_confirm, status],
    )

    def connection_test(profile_id, locale, paid=False):
        runtime_t = get_translator(locale)
        if not profile_id:
            return runtime_t("connection.select_first")
        profile = manager.load().profile(profile_id, role)
        secret = (
            manager.secret_store.get(profile.credential_ref) if profile.credential_ref else None
        )
        try:
            if role == ConnectionRole.IMAGE and not paid:
                validate_connection(manager, profile)
                return runtime_t("connection.test_local_ok")
            test_connection(manager, profile)
            return runtime_t("connection.test_ok")
        except Exception as exc:
            return runtime_t("connection.test_failed", error=sanitize_connection_error(exc, secret))

    if role == ConnectionRole.VLM:
        test_button.click(
            connection_test,
            inputs=[profile_pick, locale_selector],
            outputs=[status],
        )
    else:
        test_button.click(
            lambda profile_id, locale: (
                connection_test(profile_id, locale, False),
                gr.update(visible=bool(profile_id)),
            ),
            inputs=[profile_pick, locale_selector],
            outputs=[status, paid_confirm],
        )
        paid_cancel.click(lambda: gr.update(visible=False), outputs=[paid_confirm], queue=False)
        paid_apply.click(
            lambda profile_id, locale: (
                connection_test(profile_id, locale, True),
                gr.update(visible=False),
            ),
            inputs=[profile_pick, locale_selector],
            outputs=[status, paid_confirm],
        )

    for field in [name, provider, base_url, model, timeout, api_key, size_mode]:
        field.input(lambda: t("connection.unsaved"), outputs=[status], queue=False)

    return ConnectionEditorComponents(
        role,
        profile_pick,
        name,
        provider,
        base_url,
        model,
        timeout,
        key_status,
        size_mode,
        status,
        api_key,
    )


def refresh_connection_editor(gr, manager, editor: ConnectionEditorComponents, t):
    selected = _active_profile(manager, editor.role)
    values = _editor_values(manager, editor.role, selected, t)
    return (
        gr.update(choices=profile_choices(manager, editor.role), value=selected),
        *values,
        "",
    )
