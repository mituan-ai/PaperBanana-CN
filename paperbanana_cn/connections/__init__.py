"""Persistent role-specific connections and shared runtime resolution."""

from paperbanana_cn.connections.manager import ConnectionManager
from paperbanana_cn.connections.models import (
    ConnectionProfile,
    ConnectionRole,
    ConnectionUserConfig,
)
from paperbanana_cn.connections.resolver import load_runtime_settings, resolve_connection_settings

__all__ = [
    "ConnectionManager",
    "ConnectionProfile",
    "ConnectionRole",
    "ConnectionUserConfig",
    "load_runtime_settings",
    "resolve_connection_settings",
]
