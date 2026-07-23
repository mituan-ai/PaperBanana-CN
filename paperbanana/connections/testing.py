"""Connection validation and explicit network smoke tests."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from enum import Enum

from PIL import Image

from paperbanana.connections.manager import ConnectionManager
from paperbanana.connections.models import ConnectionProfile, ConnectionRole
from paperbanana.connections.resolver import resolve_connection_settings
from paperbanana.core.config import Settings
from paperbanana.providers.registry import ProviderRegistry


class ConnectionErrorKind(str, Enum):
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    PROTOCOL = "protocol_mismatch"
    CAPABILITY = "capability_unsupported"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ConnectionTestError(RuntimeError):
    kind: ConnectionErrorKind
    message: str
    retryable: bool = False
    status_code: int | None = None

    def __str__(self) -> str:
        status = f" (HTTP {self.status_code})" if self.status_code else ""
        return f"{self.kind.value}{status}: {self.message}"


def sanitize_connection_error(error: Exception, secret: str | None = None) -> str:
    message = str(error)
    if secret:
        message = message.replace(secret, "***")
    message = re.sub(r"(?i)(authorization:\s*bearer\s+)[^\s,;]+", r"\1***", message)
    message = re.sub(r"(?i)(api[_ -]?key[=:]\s*)[^\s,;]+", r"\1***", message)
    return message[:800]


def classify_connection_error(error: Exception, secret: str | None = None) -> ConnectionTestError:
    if isinstance(error, ConnectionTestError):
        return error
    last_attempt = getattr(error, "last_attempt", None)
    if last_attempt is not None:
        nested = last_attempt.exception()
        if isinstance(nested, Exception):
            error = nested
    safe_message = sanitize_connection_error(error, secret)
    status_code = _status_code(error)
    if status_code in {401, 403}:
        return ConnectionTestError(
            ConnectionErrorKind.AUTHENTICATION, safe_message, status_code=status_code
        )
    if status_code == 404:
        return ConnectionTestError(
            ConnectionErrorKind.NOT_FOUND, safe_message, status_code=status_code
        )
    if status_code == 429:
        return ConnectionTestError(
            ConnectionErrorKind.RATE_LIMITED,
            safe_message,
            retryable=True,
            status_code=status_code,
        )
    if status_code is not None and 400 <= status_code < 500:
        return ConnectionTestError(
            ConnectionErrorKind.PROTOCOL, safe_message, status_code=status_code
        )
    if status_code is not None and status_code >= 500:
        return ConnectionTestError(
            ConnectionErrorKind.NETWORK,
            safe_message,
            retryable=True,
            status_code=status_code,
        )
    if (
        isinstance(error, (TimeoutError, asyncio.TimeoutError))
        or "timeout" in type(error).__name__.lower()
        or "timeout" in safe_message.lower()
    ):
        return ConnectionTestError(ConnectionErrorKind.TIMEOUT, safe_message, retryable=True)
    if "does not support" in safe_message.lower() or "unsupported" in safe_message.lower():
        return ConnectionTestError(ConnectionErrorKind.CAPABILITY, safe_message)
    if isinstance(error, (ValueError, ImportError)):
        return ConnectionTestError(ConnectionErrorKind.CONFIGURATION, safe_message)
    if error.__class__.__module__.startswith(("httpx", "httpcore")):
        return ConnectionTestError(ConnectionErrorKind.NETWORK, safe_message, retryable=True)
    return ConnectionTestError(ConnectionErrorKind.UNKNOWN, safe_message)


def _status_code(error: Exception) -> int | None:
    value = getattr(error, "status_code", None)
    if isinstance(value, int):
        return value
    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def runtime_settings_for_profile(
    manager: ConnectionManager, profile: ConnectionProfile
) -> Settings:
    """Resolve one saved profile through the same path used by all entry points."""
    return resolve_connection_settings(
        Settings(),
        manager=manager,
        vlm_profile_id=profile.id if profile.role == ConnectionRole.VLM else None,
        image_profile_id=profile.id if profile.role == ConnectionRole.IMAGE else None,
        required_roles=(profile.role,),
    )


def validate_connection(manager: ConnectionManager, profile: ConnectionProfile) -> None:
    secret = _profile_secret(manager, profile)
    try:
        settings = runtime_settings_for_profile(manager, profile)
        if profile.role == ConnectionRole.VLM:
            ProviderRegistry.create_vlm(settings)
        else:
            ProviderRegistry.create_image_gen(settings)
    except Exception as exc:
        raise classify_connection_error(exc, secret) from exc


def test_connection(manager: ConnectionManager, profile: ConnectionProfile) -> None:
    """Run the smallest real request that proves the selected role works."""
    asyncio.run(_test_connection(manager, profile))


async def _test_connection(manager: ConnectionManager, profile: ConnectionProfile) -> None:
    secret = _profile_secret(manager, profile)
    try:
        settings = runtime_settings_for_profile(manager, profile)
        if profile.role == ConnectionRole.VLM:
            provider = ProviderRegistry.create_vlm(settings)
            image = Image.new("RGB", (16, 16), color="white")
            await provider.generate(
                "Return a JSON object with the single key status and value ok.",
                images=[image],
                max_tokens=64,
                response_format="json",
            )
            return
        provider = ProviderRegistry.create_image_gen(settings)
        resolution = provider.supported_resolutions[0]
        provider.validate_output_options("1:1", resolution)
        await provider.generate(
            "A minimal black line square on a plain white background.",
            width=1024,
            height=1024,
            aspect_ratio="1:1",
        )
    except Exception as exc:
        raise classify_connection_error(exc, secret) from exc


def _profile_secret(manager: ConnectionManager, profile: ConnectionProfile) -> str | None:
    try:
        profile = manager.load().profile(profile.id, profile.role)
    except KeyError:
        return None
    if not profile.credential_ref:
        return None
    try:
        return manager.secret_store.get(profile.credential_ref)
    except Exception:
        return None
