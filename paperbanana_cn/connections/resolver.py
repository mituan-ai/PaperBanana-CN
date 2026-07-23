"""Resolve saved VLM and image profiles into the existing Settings model."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import SecretStr

from paperbanana_cn.connections.manager import ConnectionManager
from paperbanana_cn.connections.models import ConnectionProfile, ConnectionRole
from paperbanana_cn.core.config import Settings

_LEGACY_CONNECTION_KEYS = {"provider", "model", "base_url", "api_key"}


def reject_profile_yaml_connections(config_path: str | Path | None) -> None:
    """Keep profile and legacy connection sources mutually exclusive."""
    if not config_path:
        return
    path = Path(config_path).expanduser()
    if not path.exists():
        return
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    conflicts = []
    for section in ("vlm", "image"):
        values = payload.get(section)
        if isinstance(values, dict):
            conflicts.extend(f"{section}.{key}" for key in values if key in _LEGACY_CONNECTION_KEYS)
    if conflicts:
        raise ValueError(
            "Profile mode cannot use connection fields from YAML: " + ", ".join(conflicts)
        )


def resolve_connection_settings(
    settings: Settings,
    *,
    manager: ConnectionManager | None = None,
    vlm_profile_id: str | None = None,
    image_profile_id: str | None = None,
    legacy: bool = False,
    required_roles: Collection[ConnectionRole] = (
        ConnectionRole.VLM,
        ConnectionRole.IMAGE,
    ),
) -> Settings:
    """Return Settings with exactly one explicit connection source."""
    if legacy:
        if vlm_profile_id or image_profile_id:
            raise ValueError("Profile IDs cannot be combined with legacy connection mode")
        return settings.model_copy(update={"connection_source": "legacy"})

    connection_manager = manager or ConnectionManager()
    config = connection_manager.load()
    required = set(required_roles)
    unknown = required - {ConnectionRole.VLM, ConnectionRole.IMAGE}
    if unknown:
        raise ValueError(
            "Unknown required connection roles: " + ", ".join(sorted(str(role) for role in unknown))
        )

    selected = {
        ConnectionRole.VLM: vlm_profile_id or config.active_vlm_profile_id,
        ConnectionRole.IMAGE: image_profile_id or config.active_image_profile_id,
    }
    missing = [role.value for role in required if not selected[role]]
    if missing:
        roles = " and ".join(sorted(missing))
        raise ValueError(
            f"Active {roles} connection profile(s) are required. "
            "Configure them with `paperbanana connections` or use explicit legacy mode."
        )

    updates: dict[str, object] = {"connection_source": "profiles"}
    for role, profile_id in selected.items():
        if role not in required and not (
            (role == ConnectionRole.VLM and vlm_profile_id)
            or (role == ConnectionRole.IMAGE and image_profile_id)
        ):
            continue
        if profile_id:
            updates.update(_profile_updates(config.profile(profile_id, role), connection_manager))
    return settings.model_copy(update=updates)


def load_runtime_settings(
    *,
    config_path: str | Path | None = None,
    overrides: Mapping[str, Any] | None = None,
    manager: ConnectionManager | None = None,
    vlm_profile_id: str | None = None,
    image_profile_id: str | None = None,
    legacy: bool = False,
    required_roles: Collection[ConnectionRole] = (
        ConnectionRole.VLM,
        ConnectionRole.IMAGE,
    ),
) -> Settings:
    """Load runtime settings and resolve the only selected connection source."""
    normalized_path = Path(config_path).expanduser() if config_path else None
    values = dict(overrides or {})
    if normalized_path:
        settings = Settings.from_yaml(normalized_path, **values)
    else:
        settings = Settings(**values)
    if not legacy:
        reject_profile_yaml_connections(normalized_path)
    return resolve_connection_settings(
        settings,
        manager=manager,
        vlm_profile_id=vlm_profile_id,
        image_profile_id=image_profile_id,
        legacy=legacy,
        required_roles=required_roles,
    )


def _profile_updates(profile: ConnectionProfile, manager: ConnectionManager) -> dict[str, object]:
    prefix = profile.role.value
    secret = None
    if profile.credential_ref:
        secret = SecretStr(manager.secret_store.get(profile.credential_ref))
    updates: dict[str, object] = {
        f"{prefix}_provider": profile.provider,
        f"{prefix}_base_url": profile.base_url,
        f"{prefix}_api_key": secret,
        f"{prefix}_model": profile.model,
        f"{prefix}_timeout_seconds": profile.timeout_seconds,
    }
    if profile.role == ConnectionRole.IMAGE:
        updates["image_size_mode"] = profile.image_size_mode
    return updates
