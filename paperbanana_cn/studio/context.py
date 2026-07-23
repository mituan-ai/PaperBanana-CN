"""Typed shared context for Studio page builders."""

from __future__ import annotations

import math
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from paperbanana_cn.connections.manager import ConnectionManager
from paperbanana_cn.connections.models import ConnectionRole
from paperbanana_cn.core.config import Settings
from paperbanana_cn.i18n.translator import Translator
from paperbanana_cn.studio.models import StudioRunOptions
from paperbanana_cn.studio.runner import build_settings


@dataclass(frozen=True)
class StudioContext:
    """Application services and immutable launch defaults shared by Studio pages."""

    manager: ConnectionManager
    translator: Translator
    frontend_translator: Callable[[str], Any]
    locale: str
    default_output_dir: str
    default_config_path: str

    @property
    def t(self):
        """Translate static text in the browser and formatted text on the server."""

        def translate(key: str, **values: object):
            if values:
                return self.translator(key, **values)
            return self.frontend_translator(key)

        return translate

    def translator_for(self, locale: str) -> Translator:
        """Return a server-side translator for one browser callback."""
        from paperbanana_cn.i18n import get_translator

        return get_translator(locale)

    def has_active_connections(self, required_roles: Collection[ConnectionRole]) -> bool:
        """Return whether every role has a valid active profile reference."""
        config = self.manager.load()
        selected = {
            ConnectionRole.VLM: config.active_vlm_profile_id,
            ConnectionRole.IMAGE: config.active_image_profile_id,
        }
        for role in required_roles:
            profile_id = selected[role]
            if not profile_id:
                return False
            try:
                config.profile(profile_id, role)
            except (KeyError, ValueError):
                return False
        return True

    def resolve_settings(
        self,
        options: StudioRunOptions,
        required_roles: Collection[ConnectionRole],
    ) -> Settings:
        return build_settings(
            config_path=(options.config_path or "").strip() or None,
            output_dir=(options.output_dir or self.default_output_dir).strip()
            or self.default_output_dir,
            vlm_provider="",
            vlm_model="",
            image_provider="",
            image_model="",
            output_format=options.output_format,
            refinement_iterations=max(1, int(options.refinement_iterations)),
            auto_refine=options.auto_refine,
            max_iterations=max(1, int(options.max_iterations)),
            optimize_inputs=options.optimize_inputs,
            save_prompts=options.save_prompts,
            output_resolution=options.output_resolution,
            seed=options.seed,
            connection_manager=self.manager,
            vlm_profile_id=options.vlm_profile_id or None,
            image_profile_id=options.image_profile_id or None,
            legacy_connections=False,
            required_roles=tuple(required_roles),
        )


def optional_upload_path(file_obj: Any) -> str | None:
    """Normalize a Gradio upload value without coupling pages to its concrete type."""
    if file_obj is None:
        return None
    if isinstance(file_obj, str):
        return file_obj if file_obj.strip() else None
    return getattr(file_obj, "name", None) or str(file_obj)


def output_root(value: str, default: str) -> str:
    return (value or default).strip() or default


def optional_int(value: float | None) -> int | None:
    return _optional_int(value)


def _optional_int(value: float | None) -> int | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def existing_file(path: str | None) -> str | None:
    if not path:
        return None
    return path if Path(path).is_file() else None
