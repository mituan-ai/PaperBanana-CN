"""Desktop application shell, navigation, and persisted UI state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paperbanana.studio.branding import BRAND_LOGO_URL
from paperbanana.studio.context import StudioContext
from paperbanana.studio.models import WORKFLOW_BY_KEY, WORKFLOW_SPECS

GROUP_ORDER = ("nav.generate", "nav.improve", "nav.automation", "nav.tools", "nav.system")


@dataclass(frozen=True)
class HeaderComponents:
    page_title: Any
    vlm_profile: Any
    image_profile: Any
    locale: Any


def build_sidebar(gr, ctx: StudioContext) -> dict[str, Any]:
    gr.HTML(
        f"""
        <div class="brand-lockup">
          <img class="brand-mark" src="{BRAND_LOGO_URL}" alt="PaperBanana-CN logo">
          <div>
            <div class="brand-name">PaperBanana-CN</div>
            <div class="brand-edition">Research Studio</div>
          </div>
        </div>
        """,
        elem_id="studio-brand",
    )
    buttons: dict[str, Any] = {}
    for group_key in GROUP_ORDER:
        gr.Markdown(ctx.t(group_key), elem_classes="nav-group-label")
        for spec in (item for item in WORKFLOW_SPECS if item.group_key == group_key):
            buttons[spec.key] = gr.Button(
                ctx.t(spec.label_key),
                variant="primary" if spec.key == "diagram" else "secondary",
                size="sm",
                elem_id=f"nav-{spec.key}",
                elem_classes="nav-item",
            )
    gr.HTML(
        """
        <div class="sidebar-disclaimer">
          <a href="https://github.com/mituan-ai/PaperBanana-CN" target="_blank"
             rel="noreferrer">github.com/mituan-ai</a>
          <p class="developer-credit">开发者 mituan</p>
        </div>
        """,
        elem_id="sidebar-disclaimer",
    )
    return buttons


def build_header(gr, ctx: StudioContext) -> HeaderComponents:
    config = ctx.manager.load()
    with gr.Row(elem_id="studio-header", elem_classes="studio-header"):
        page_title = gr.Markdown(
            f"# {ctx.t('tab.diagram')}",
            elem_id="current-page-title",
            elem_classes="header-title",
        )
        vlm_profile = gr.State(config.active_vlm_profile_id)
        image_profile = gr.State(config.active_image_profile_id)
        locale = gr.State(ctx.locale)
    return HeaderComponents(page_title, vlm_profile, image_profile, locale)


def navigation_updates(gr, ctx: StudioContext, selected: str):
    spec = WORKFLOW_BY_KEY[selected]
    page_updates = [gr.update(visible=item.key == selected) for item in WORKFLOW_SPECS]
    button_updates = [
        gr.update(variant="primary" if item.key == selected else "secondary")
        for item in WORKFLOW_SPECS
    ]
    return (
        f"# {ctx.t(spec.label_key)}",
        *page_updates,
        *button_updates,
    )


def navigation_buttons_in_order(buttons: dict[str, Any]) -> list[Any]:
    return [buttons[spec.key] for spec in WORKFLOW_SPECS]


def refresh_active_profiles(ctx: StudioContext):
    config = ctx.manager.load()
    return config.active_vlm_profile_id, config.active_image_profile_id
