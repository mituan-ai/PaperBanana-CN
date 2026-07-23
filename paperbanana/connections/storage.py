"""Atomic storage for connection profiles and API secrets."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from filelock import FileLock
from platformdirs import user_config_dir, user_data_dir
from pydantic import ValidationError

from paperbanana.connections.models import ConnectionUserConfig


class ConnectionStorageError(RuntimeError):
    """Base class for persistent connection failures."""


class CorruptConnectionConfigError(ConnectionStorageError):
    """The persisted document exists but cannot be validated."""


class ConnectionRevisionError(ConnectionStorageError):
    """Another process saved a newer revision."""


class MissingCredentialError(ConnectionStorageError):
    """A profile references a credential that no longer exists."""


@dataclass(frozen=True)
class ConnectionPaths:
    config_file: Path
    secret_file: Path

    @classmethod
    def defaults(cls) -> ConnectionPaths:
        return cls(
            config_file=Path(user_config_dir("paperbanana-cn")) / "connections.json",
            secret_file=Path(user_data_dir("paperbanana-cn")) / "secrets.json",
        )


def _atomic_write_json(path: Path, payload: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


class ConnectionConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = FileLock(f"{path}.lock")

    def load(self) -> ConnectionUserConfig:
        if not self.path.exists():
            return ConnectionUserConfig()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return ConnectionUserConfig.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise CorruptConnectionConfigError(
                f"Connection config is invalid and was not reset: {self.path}: {exc}"
            ) from exc

    def save(self, config: ConnectionUserConfig, expected_revision: int) -> ConnectionUserConfig:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._lock:
            current = self.load()
            if current.revision != expected_revision:
                raise ConnectionRevisionError(
                    f"Connection config changed from revision {expected_revision} "
                    f"to {current.revision}; reload before saving"
                )
            saved = config.model_copy(update={"revision": current.revision + 1})
            _atomic_write_json(self.path, saved.model_dump(mode="json"))
            return saved


class SecretStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = FileLock(f"{path}.lock")

    def get(self, reference: str) -> str:
        secrets = self._load()
        try:
            return secrets[reference]
        except KeyError as exc:
            raise MissingCredentialError(f"Credential reference is missing: {reference}") from exc

    def set(self, secret: str, reference: str | None = None) -> str:
        normalized = secret.strip()
        if not normalized:
            raise ValueError("API key must not be blank")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._lock:
            secrets = self._load()
            key = reference or str(uuid4())
            secrets[key] = normalized
            _atomic_write_json(self.path, {"schema_version": 1, "secrets": secrets})
            return key

    def delete(self, reference: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._lock:
            secrets = self._load()
            if reference not in secrets:
                return
            del secrets[reference]
            _atomic_write_json(self.path, {"schema_version": 1, "secrets": secrets})

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != 1 or not isinstance(payload.get("secrets"), dict):
                raise ValueError("unsupported secret store schema")
            if not all(
                isinstance(k, str) and isinstance(v, str) for k, v in payload["secrets"].items()
            ):
                raise ValueError("secret store entries must be strings")
            return payload["secrets"]
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise CorruptConnectionConfigError(
                f"Secret store is invalid and was not reset: {self.path}: {exc}"
            ) from exc
