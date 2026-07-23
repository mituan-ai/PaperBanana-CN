"""Connection profiles, secret isolation, and runtime resolution."""

from __future__ import annotations

import json
import os
import stat
import threading
from base64 import b64encode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO

import pytest
from PIL import Image
from pydantic import ValidationError

from paperbanana_cn.connections.manager import ConnectionManager
from paperbanana_cn.connections.models import ConnectionProfile, ConnectionRole
from paperbanana_cn.connections.resolver import load_runtime_settings, resolve_connection_settings
from paperbanana_cn.connections.storage import (
    ConnectionRevisionError,
    CorruptConnectionConfigError,
    MissingCredentialError,
)
from paperbanana_cn.connections.testing import (
    ConnectionErrorKind,
    ConnectionTestError,
    classify_connection_error,
)
from paperbanana_cn.core.config import Settings
from paperbanana_cn.providers.registry import ProviderRegistry


@pytest.fixture
def manager(tmp_path):
    return ConnectionManager(
        config_path=tmp_path / "config" / "connections.json",
        secret_path=tmp_path / "data" / "secrets.json",
    )


def _profile(role: ConnectionRole, **overrides) -> ConnectionProfile:
    defaults = {
        "name": f"{role.value}-relay",
        "role": role,
        "provider": "openai" if role == ConnectionRole.VLM else "openai_imagen",
        "base_url": f"https://{role.value}.relay.example/v1",
        "model": "vision-model" if role == ConnectionRole.VLM else "image-model",
    }
    defaults.update(overrides)
    return ConnectionProfile(**defaults)


def test_profile_rejects_invalid_url():
    with pytest.raises(ValidationError, match="absolute HTTP"):
        _profile(ConnectionRole.VLM, base_url="relay.example/v1")


def test_profile_rejects_image_options_for_vlm():
    with pytest.raises(ValidationError, match="only valid for image"):
        _profile(ConnectionRole.VLM, image_size_mode="explicit_pixels")


def test_profiles_and_secrets_persist_separately(manager):
    profile = _profile(ConnectionRole.VLM)
    saved = manager.save_profile(profile, api_key="secret-vlm-key")

    stored = saved.profile(profile.id, ConnectionRole.VLM)
    config_text = manager.config_store.path.read_text(encoding="utf-8")
    secret_text = manager.secret_store.path.read_text(encoding="utf-8")
    assert "secret-vlm-key" not in config_text
    assert stored.credential_ref in config_text
    assert "secret-vlm-key" in secret_text
    assert manager.secret_store.get(stored.credential_ref) == "secret-vlm-key"
    if os.name == "posix":
        assert stat.S_IMODE(manager.secret_store.path.stat().st_mode) == 0o600


def test_saved_profiles_survive_new_manager_instance(manager):
    profile = _profile(ConnectionRole.VLM)
    manager.save_profile(profile, api_key="secret")
    reloaded = ConnectionManager(manager.config_store.path, manager.secret_store.path).load()
    assert reloaded.active_vlm_profile_id == profile.id
    assert reloaded.profile(profile.id, ConnectionRole.VLM).model == "vision-model"


def test_revision_conflict_does_not_overwrite(manager):
    original = manager.load()
    manager.save_preferences(locale="en", expected_revision=original.revision)
    with pytest.raises(ConnectionRevisionError, match="reload before saving"):
        manager.save_preferences(locale="zh-CN", expected_revision=original.revision)
    assert manager.load().locale == "en"


def test_corrupt_config_is_reported_without_reset(manager):
    manager.config_store.path.parent.mkdir(parents=True)
    manager.config_store.path.write_text("{broken", encoding="utf-8")
    with pytest.raises(CorruptConnectionConfigError, match="was not reset"):
        manager.load()
    assert manager.config_store.path.read_text(encoding="utf-8") == "{broken"


def test_resolver_builds_two_independent_connections(manager, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://ignored.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "ignored-key")
    vlm = _profile(ConnectionRole.VLM, model="vlm-a")
    image = _profile(
        ConnectionRole.IMAGE,
        model="image-b",
        image_size_mode="explicit_pixels",
    )
    manager.save_profile(vlm, api_key="vlm-key")
    manager.save_profile(image, api_key="image-key")

    resolved = resolve_connection_settings(Settings(), manager=manager)
    assert resolved.connection_source == "profiles"
    assert resolved.vlm_base_url == "https://vlm.relay.example/v1"
    assert resolved.image_base_url == "https://image.relay.example/v1"
    assert resolved.vlm_api_key.get_secret_value() == "vlm-key"
    assert resolved.image_api_key.get_secret_value() == "image-key"
    assert resolved.effective_vlm_model == "vlm-a"
    assert resolved.effective_image_model == "image-b"
    assert resolved.openai_base_url == "https://ignored.example/v1"

    vlm_provider = ProviderRegistry.create_vlm(resolved)
    image_provider = ProviderRegistry.create_image_gen(resolved)
    assert vlm_provider._base_url == "https://vlm.relay.example/v1"
    assert vlm_provider._api_key == "vlm-key"
    assert image_provider._base_url == "https://image.relay.example/v1"
    assert image_provider._api_key == "image-key"


def test_same_relay_keeps_role_models_and_credentials_independent(manager):
    shared_url = "https://shared.relay.example/v1"
    vlm = _profile(
        ConnectionRole.VLM,
        base_url=shared_url,
        model="shared-vlm-model",
    )
    image = _profile(
        ConnectionRole.IMAGE,
        base_url=shared_url,
        model="shared-image-model",
        image_size_mode="explicit_pixels",
    )
    manager.save_profile(vlm, api_key="shared-vlm-key")
    manager.save_profile(image, api_key="shared-image-key")

    resolved = resolve_connection_settings(Settings(), manager=manager)

    assert resolved.vlm_base_url == resolved.image_base_url == shared_url
    assert resolved.effective_vlm_model == "shared-vlm-model"
    assert resolved.effective_image_model == "shared-image-model"
    assert resolved.vlm_api_key.get_secret_value() == "shared-vlm-key"
    assert resolved.image_api_key.get_secret_value() == "shared-image-key"


def test_google_vlm_and_openai_image_profiles_can_be_mixed(manager):
    vlm = _profile(
        ConnectionRole.VLM,
        provider="gemini",
        base_url="https://gemini.relay.example",
        model="gemini-vision-model",
    )
    image = _profile(
        ConnectionRole.IMAGE,
        provider="openai_imagen",
        base_url="https://openai-image.relay.example/v1",
        model="openai-image-model",
        image_size_mode="explicit_pixels",
    )
    manager.save_profile(vlm, api_key="gemini-role-key")
    manager.save_profile(image, api_key="openai-role-key")

    resolved = resolve_connection_settings(Settings(), manager=manager)
    vlm_provider = ProviderRegistry.create_vlm(resolved)
    image_provider = ProviderRegistry.create_image_gen(resolved)

    assert vlm_provider.name == "gemini"
    assert vlm_provider.model_name == "gemini-vision-model"
    assert vlm_provider._api_key == "gemini-role-key"
    assert image_provider.name == "openai_imagen"
    assert image_provider.model_name == "openai-image-model"
    assert image_provider._api_key == "openai-role-key"


def test_resolver_requires_both_active_roles(manager):
    manager.save_profile(_profile(ConnectionRole.VLM), api_key="key")
    with pytest.raises(ValueError, match="Active image connection"):
        resolve_connection_settings(Settings(), manager=manager)


def test_delete_profile_removes_unshared_secret(manager):
    profile = _profile(ConnectionRole.VLM)
    saved = manager.save_profile(profile, api_key="secret")
    reference = saved.profile(profile.id, ConnectionRole.VLM).credential_ref
    manager.delete_profile(profile.id)
    payload = json.loads(manager.secret_store.path.read_text(encoding="utf-8"))
    assert reference not in payload["secrets"]


def test_api_key_update_uses_new_reference_and_removes_old(manager):
    profile = _profile(ConnectionRole.VLM)
    first = manager.save_profile(profile, api_key="old-secret")
    old_reference = first.profile(profile.id, ConnectionRole.VLM).credential_ref

    second = manager.save_profile(profile, api_key="new-secret")
    new_reference = second.profile(profile.id, ConnectionRole.VLM).credential_ref

    assert new_reference != old_reference
    assert manager.secret_store.get(new_reference) == "new-secret"
    payload = json.loads(manager.secret_store.path.read_text(encoding="utf-8"))
    assert old_reference not in payload["secrets"]


def test_revision_conflict_does_not_mutate_existing_secret(manager):
    profile = _profile(ConnectionRole.VLM)
    original = manager.save_profile(profile, api_key="old-secret")
    old_reference = original.profile(profile.id, ConnectionRole.VLM).credential_ref
    manager.save_preferences(locale="en")

    with pytest.raises(ConnectionRevisionError):
        manager.save_profile(
            profile,
            api_key="new-secret",
            expected_revision=original.revision,
        )

    current = manager.load().profile(profile.id, ConnectionRole.VLM)
    assert current.credential_ref == old_reference
    assert manager.secret_store.get(old_reference) == "old-secret"
    assert "new-secret" not in manager.secret_store.path.read_text(encoding="utf-8")


def test_invalid_profile_update_is_rejected_before_config_write(manager):
    first = _profile(ConnectionRole.VLM, name="first")
    second = _profile(ConnectionRole.VLM, name="second")
    manager.save_profile(first, api_key="first-secret")
    manager.save_profile(second, api_key="second-secret")
    before = manager.config_store.path.read_text(encoding="utf-8")

    invalid = second.model_copy(update={"name": "first", "base_url": "not-a-url"})
    with pytest.raises(ValidationError):
        manager.save_profile(invalid, api_key="replacement-secret")

    assert manager.config_store.path.read_text(encoding="utf-8") == before
    assert "replacement-secret" not in manager.secret_store.path.read_text(encoding="utf-8")


def test_profile_mode_never_falls_back_to_legacy_environment(manager, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-secret")
    with pytest.raises(ValueError, match="Active image and vlm connection"):
        load_runtime_settings(manager=manager)

    legacy = load_runtime_settings(manager=manager, legacy=True)
    assert legacy.connection_source == "legacy"
    assert legacy.openai_api_key == "legacy-secret"


def test_missing_profile_credential_is_reported(manager):
    profile = _profile(ConnectionRole.VLM)
    saved = manager.save_profile(profile, api_key="secret")
    reference = saved.profile(profile.id, ConnectionRole.VLM).credential_ref
    manager.secret_store.delete(reference)

    with pytest.raises(MissingCredentialError, match="reference is missing"):
        resolve_connection_settings(
            Settings(),
            manager=manager,
            required_roles=(ConnectionRole.VLM,),
        )


def test_explicit_profile_id_overrides_active_profile(manager):
    active = _profile(ConnectionRole.VLM, name="active", model="active-model")
    selected = _profile(ConnectionRole.VLM, name="selected", model="selected-model")
    manager.save_profile(active, api_key="active-key")
    manager.save_profile(selected, api_key="selected-key", make_active=False)

    resolved = resolve_connection_settings(
        Settings(),
        manager=manager,
        vlm_profile_id=selected.id,
        required_roles=(ConnectionRole.VLM,),
    )
    assert resolved.effective_vlm_model == "selected-model"
    assert resolved.vlm_api_key.get_secret_value() == "selected-key"


def test_profile_yaml_connection_fields_are_rejected_but_legacy_accepts_them(manager, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        "vlm:\n  provider: openai\n  model: yaml-vlm\n"
        "image:\n  provider: openai_imagen\n  model: yaml-image\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Profile mode cannot use connection fields"):
        load_runtime_settings(config_path=config, manager=manager)

    legacy = load_runtime_settings(config_path=config, manager=manager, legacy=True)
    assert legacy.connection_source == "legacy"
    assert legacy.vlm_provider == "openai"
    assert legacy.image_provider == "openai_imagen"


def test_preferences_persist_ratio_resolution_and_locale(manager):
    manager.save_preferences(locale="en", aspect_ratio="4:5", output_resolution="4K")
    reloaded = ConnectionManager(
        manager.config_store.path,
        manager.secret_store.path,
    ).load()
    assert reloaded.locale == "en"
    assert reloaded.last_aspect_ratio == "4:5"
    assert reloaded.last_output_resolution == "4k"


class _FakeRelay:
    def __init__(self, *, image_response: bool = False, status: int = 200):
        self.image_response = image_response
        self.status = status
        self.requests: list[dict] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                owner.requests.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "body": body,
                    }
                )
                if owner.status != 200:
                    self._send(owner.status, {"error": {"message": "denied"}})
                elif owner.image_response:
                    buffer = BytesIO()
                    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
                    data_url = "data:image/png;base64," + b64encode(buffer.getvalue()).decode()
                    self._send(
                        200,
                        {
                            "choices": [
                                {
                                    "message": {
                                        "content": "",
                                        "images": [{"image_url": {"url": data_url}}],
                                    }
                                }
                            ]
                        },
                    )
                else:
                    self._send(
                        200,
                        {
                            "choices": [{"message": {"content": '{"status":"ok"}'}}],
                            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                        },
                    )

            def _send(self, status, payload):
                encoded = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format, *args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        _, port = self.server.server_address
        return f"http://localhost:{port}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def test_two_fake_relays_receive_independent_urls_keys_and_models(manager):
    from paperbanana_cn.connections.testing import test_connection as run_connection_test

    with _FakeRelay() as vlm_relay, _FakeRelay(image_response=True) as image_relay:
        vlm = _profile(
            ConnectionRole.VLM,
            provider="openrouter",
            base_url=vlm_relay.base_url,
            model="vlm-through-relay",
        )
        image = _profile(
            ConnectionRole.IMAGE,
            provider="openrouter_imagen",
            base_url=image_relay.base_url,
            model="image-through-relay",
            image_size_mode="prompt_hint",
        )
        manager.save_profile(vlm, api_key="vlm-relay-key")
        manager.save_profile(image, api_key="image-relay-key")

        run_connection_test(manager, vlm)
        run_connection_test(manager, image)

    assert vlm_relay.requests == [
        {
            "path": "/v1/chat/completions",
            "authorization": "Bearer vlm-relay-key",
            "body": vlm_relay.requests[0]["body"],
        }
    ]
    assert vlm_relay.requests[0]["body"]["model"] == "vlm-through-relay"
    assert image_relay.requests[0]["path"] == "/v1/chat/completions"
    assert image_relay.requests[0]["authorization"] == "Bearer image-relay-key"
    assert image_relay.requests[0]["body"]["model"] == "image-through-relay"


def test_authentication_failure_is_structured_redacted_and_not_retried(manager):
    from paperbanana_cn.connections.testing import test_connection as run_connection_test

    with _FakeRelay(status=401) as relay:
        profile = _profile(
            ConnectionRole.VLM,
            provider="openrouter",
            base_url=relay.base_url,
        )
        manager.save_profile(profile, api_key="do-not-leak")
        with pytest.raises(ConnectionTestError) as exc_info:
            run_connection_test(manager, profile)

    error = exc_info.value
    assert error.kind == ConnectionErrorKind.AUTHENTICATION
    assert error.status_code == 401
    assert error.retryable is False
    assert "do-not-leak" not in str(error)
    assert len(relay.requests) == 1


class _StatusError(RuntimeError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"request failed with {status_code}")


@pytest.mark.parametrize(
    ("error", "kind", "retryable"),
    [
        (_StatusError(404), ConnectionErrorKind.NOT_FOUND, False),
        (_StatusError(429), ConnectionErrorKind.RATE_LIMITED, True),
        (_StatusError(400), ConnectionErrorKind.PROTOCOL, False),
        (TimeoutError("request timeout"), ConnectionErrorKind.TIMEOUT, True),
        (
            ValueError("provider does not support image edits"),
            ConnectionErrorKind.CAPABILITY,
            False,
        ),
    ],
)
def test_connection_error_classification(error, kind, retryable):
    classified = classify_connection_error(error)
    assert classified.kind == kind
    assert classified.retryable is retryable
