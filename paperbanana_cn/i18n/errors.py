"""User-facing error translation without leaking connection credentials."""

from __future__ import annotations

from pydantic import ValidationError

from paperbanana_cn.connections.storage import (
    ConnectionRevisionError,
    CorruptConnectionConfigError,
    MissingCredentialError,
)
from paperbanana_cn.connections.testing import ConnectionTestError, sanitize_connection_error
from paperbanana_cn.i18n.translator import Translator


def localize_error(error: Exception, t: Translator) -> str:
    """Return an actionable locale message while preserving safe diagnostics."""
    safe = sanitize_connection_error(error)
    if isinstance(error, MissingCredentialError):
        return t("error.credential_missing", error=safe)
    if isinstance(error, CorruptConnectionConfigError):
        return t("error.connection_config", error=safe)
    if isinstance(error, ConnectionRevisionError):
        return t("error.connection_conflict", error=safe)
    if isinstance(error, ConnectionTestError):
        return t("error.connection_test", kind=error.kind.value, error=safe)
    if isinstance(error, ValidationError):
        return t("error.validation", error=safe)
    if safe.startswith("Active ") and "connection profile" in safe:
        return t("error.connections_required")
    if safe.startswith("Profile mode cannot use connection fields from YAML"):
        return t("error.profile_yaml", error=safe)
    if "does not support aspect ratio" in safe or "does not support resolution" in safe:
        return t("error.unsupported_option", error=safe)
    return t("error.unexpected", type=type(error).__name__, error=safe)
