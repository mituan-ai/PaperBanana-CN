"""Typed connection profiles and non-secret user preferences."""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from paperbanana.core.config import OUTPUT_RESOLUTION_VALUES, ImageSizeModeName
from paperbanana.core.types import SUPPORTED_ASPECT_RATIOS


class ConnectionRole(str, Enum):
    VLM = "vlm"
    IMAGE = "image"


class ConnectionProfile(BaseModel):
    """One reusable connection for exactly one pipeline role."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=80)
    role: ConnectionRole
    provider: str = Field(min_length=1, max_length=80)
    base_url: str | None = None
    model: str = Field(min_length=1, max_length=300)
    timeout_seconds: float = Field(default=180.0, gt=0, le=1800)
    credential_ref: str | None = None
    image_size_mode: ImageSizeModeName | None = None

    @field_validator("name", "provider", "model")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url must not contain a query or fragment")
        return normalized

    @model_validator(mode="after")
    def validate_role_options(self) -> ConnectionProfile:
        if self.role == ConnectionRole.VLM and self.image_size_mode is not None:
            raise ValueError("image_size_mode is only valid for image connections")
        return self


class ConnectionUserConfig(BaseModel):
    """The single non-secret persisted configuration document."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    revision: int = Field(default=0, ge=0)
    locale: str = "zh-CN"
    active_vlm_profile_id: str | None = None
    active_image_profile_id: str | None = None
    last_aspect_ratio: str = "16:9"
    last_output_resolution: str = "2k"
    studio_output_dir: str | None = None
    studio_config_path: str | None = None
    profiles: list[ConnectionProfile] = Field(default_factory=list)

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, value: str) -> str:
        if value not in {"zh-CN", "en"}:
            raise ValueError("locale must be zh-CN or en")
        return value

    @field_validator("last_aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        if value not in SUPPORTED_ASPECT_RATIOS:
            raise ValueError("last_aspect_ratio is not supported")
        return value

    @field_validator("last_output_resolution")
    @classmethod
    def validate_resolution(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in OUTPUT_RESOLUTION_VALUES:
            raise ValueError("last_output_resolution must be 1k, 2k, or 4k")
        return normalized

    @field_validator("studio_output_dir", "studio_config_path")
    @classmethod
    def normalize_optional_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_profiles(self) -> ConnectionUserConfig:
        by_id: dict[str, ConnectionProfile] = {}
        names: set[tuple[ConnectionRole, str]] = set()
        for profile in self.profiles:
            if profile.id in by_id:
                raise ValueError(f"duplicate connection profile id: {profile.id}")
            name_key = (profile.role, profile.name.casefold())
            if name_key in names:
                raise ValueError(f"duplicate {profile.role.value} profile name: {profile.name}")
            by_id[profile.id] = profile
            names.add(name_key)
        self._validate_active(by_id, self.active_vlm_profile_id, ConnectionRole.VLM)
        self._validate_active(by_id, self.active_image_profile_id, ConnectionRole.IMAGE)
        return self

    @staticmethod
    def _validate_active(
        profiles: dict[str, ConnectionProfile], profile_id: str | None, role: ConnectionRole
    ) -> None:
        if profile_id is None:
            return
        profile = profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"active {role.value} profile does not exist: {profile_id}")
        if profile.role != role:
            raise ValueError(f"active {role.value} profile has role {profile.role.value}")

    def profile(self, profile_id: str, role: ConnectionRole) -> ConnectionProfile:
        for profile in self.profiles:
            if profile.id == profile_id and profile.role == role:
                return profile
        raise KeyError(f"{role.value} connection profile not found: {profile_id}")
