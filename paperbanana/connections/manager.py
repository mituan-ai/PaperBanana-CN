"""Application service for connection profile lifecycle operations."""

from __future__ import annotations

from pathlib import Path

from filelock import FileLock

from paperbanana.connections.models import (
    ConnectionProfile,
    ConnectionRole,
    ConnectionUserConfig,
)
from paperbanana.connections.storage import (
    ConnectionConfigStore,
    ConnectionPaths,
    SecretStore,
)


class ConnectionManager:
    def __init__(
        self,
        config_path: Path | None = None,
        secret_path: Path | None = None,
    ):
        defaults = ConnectionPaths.defaults()
        self.config_store = ConnectionConfigStore(config_path or defaults.config_file)
        self.secret_store = SecretStore(secret_path or defaults.secret_file)
        self._operation_lock = FileLock(f"{self.config_store.path}.operation.lock")

    def load(self) -> ConnectionUserConfig:
        return self.config_store.load()

    def save_profile(
        self,
        profile: ConnectionProfile,
        *,
        api_key: str | None = None,
        clear_api_key: bool = False,
        make_active: bool = True,
        expected_revision: int | None = None,
    ) -> ConnectionUserConfig:
        with self._operation_lock:
            return self._save_profile_locked(
                profile,
                api_key=api_key,
                clear_api_key=clear_api_key,
                make_active=make_active,
                expected_revision=expected_revision,
            )

    def _save_profile_locked(
        self,
        profile: ConnectionProfile,
        *,
        api_key: str | None,
        clear_api_key: bool,
        make_active: bool,
        expected_revision: int | None,
    ) -> ConnectionUserConfig:
        config = self.load()
        expected = config.revision if expected_revision is None else expected_revision
        profile = ConnectionProfile.model_validate(profile.model_dump(mode="json"))
        existing = next((item for item in config.profiles if item.id == profile.id), None)
        credential_ref = profile.credential_ref or (existing.credential_ref if existing else None)
        old_reference = credential_ref
        new_reference: str | None = None
        if clear_api_key:
            credential_ref = None
        elif api_key is not None and api_key.strip():
            new_reference = self.secret_store.set(api_key)
            credential_ref = new_reference
        stored_profile = profile.model_copy(update={"credential_ref": credential_ref})
        profiles = [item for item in config.profiles if item.id != profile.id]
        profiles.append(stored_profile)
        update: dict[str, object] = {"profiles": profiles}
        if make_active:
            update[f"active_{profile.role.value}_profile_id"] = profile.id
        try:
            candidate = ConnectionUserConfig.model_validate(
                config.model_copy(update=update).model_dump(mode="json")
            )
            saved = self.config_store.save(candidate, expected)
        except Exception:
            if new_reference:
                self.secret_store.delete(new_reference)
            raise
        if (
            old_reference
            and old_reference != credential_ref
            and not any(item.credential_ref == old_reference for item in saved.profiles)
        ):
            self.secret_store.delete(old_reference)
        return saved

    def delete_profile(
        self, profile_id: str, *, expected_revision: int | None = None
    ) -> ConnectionUserConfig:
        with self._operation_lock:
            return self._delete_profile_locked(profile_id, expected_revision=expected_revision)

    def _delete_profile_locked(
        self, profile_id: str, *, expected_revision: int | None
    ) -> ConnectionUserConfig:
        config = self.load()
        expected = config.revision if expected_revision is None else expected_revision
        profile = next((item for item in config.profiles if item.id == profile_id), None)
        if profile is None:
            raise KeyError(f"Connection profile not found: {profile_id}")
        update: dict[str, object] = {
            "profiles": [item for item in config.profiles if item.id != profile_id]
        }
        if config.active_vlm_profile_id == profile_id:
            update["active_vlm_profile_id"] = None
        if config.active_image_profile_id == profile_id:
            update["active_image_profile_id"] = None
        candidate = ConnectionUserConfig.model_validate(
            config.model_copy(update=update).model_dump(mode="json")
        )
        saved = self.config_store.save(candidate, expected)
        if profile.credential_ref and not any(
            item.credential_ref == profile.credential_ref for item in saved.profiles
        ):
            self.secret_store.delete(profile.credential_ref)
        return saved

    def set_active(
        self, role: ConnectionRole, profile_id: str, *, expected_revision: int | None = None
    ) -> ConnectionUserConfig:
        with self._operation_lock:
            config = self.load()
            config.profile(profile_id, role)
            expected = config.revision if expected_revision is None else expected_revision
            candidate = ConnectionUserConfig.model_validate(
                config.model_copy(
                    update={f"active_{role.value}_profile_id": profile_id}
                ).model_dump(mode="json")
            )
            return self.config_store.save(candidate, expected)

    def save_preferences(
        self,
        *,
        locale: str | None = None,
        aspect_ratio: str | None = None,
        output_resolution: str | None = None,
        expected_revision: int | None = None,
    ) -> ConnectionUserConfig:
        with self._operation_lock:
            config = self.load()
            expected = config.revision if expected_revision is None else expected_revision
            updates = {}
            if locale is not None:
                updates["locale"] = locale
            if aspect_ratio is not None:
                updates["last_aspect_ratio"] = aspect_ratio
            if output_resolution is not None:
                updates["last_output_resolution"] = output_resolution
            candidate = ConnectionUserConfig.model_validate(
                config.model_copy(update=updates).model_dump(mode="json")
            )
            return self.config_store.save(candidate, expected)

    def save_studio_defaults(
        self,
        *,
        output_dir: str,
        config_path: str | None,
        expected_revision: int | None = None,
    ) -> ConnectionUserConfig:
        """Persist non-secret Studio defaults independently from form state."""
        with self._operation_lock:
            config = self.load()
            expected = config.revision if expected_revision is None else expected_revision
            candidate = ConnectionUserConfig.model_validate(
                config.model_copy(
                    update={
                        "studio_output_dir": output_dir,
                        "studio_config_path": config_path,
                    }
                ).model_dump(mode="json")
            )
            return self.config_store.save(candidate, expected)
