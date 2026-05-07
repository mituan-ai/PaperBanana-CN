"""Helpers for loading local configuration and secrets."""

from pathlib import Path
from typing import Any

import os
import yaml


CONFIG_DIRNAME = "configs"
LOCAL_SECRET_DIRNAME = "local"
LOCAL_PROVIDER_SETTINGS_FILENAME = "provider_settings.yaml"

SECRET_FILE_MAP = {
    ("api_keys", "google_api_key"): "google_api_key.txt",
    ("api_keys", "openai_api_key"): "openai_api_key.txt",
    ("gemini", "vlm_api_key"): "gemini_vlm_api_key.txt",
    ("gemini", "image_api_key"): "gemini_image_api_key.txt",
    ("openai", "vlm_api_key"): "openai_vlm_api_key.txt",
    ("openai", "image_api_key"): "openai_image_api_key.txt",
    ("api_keys", "anthropic_api_key"): "anthropic_api_key.txt",
    ("evolink", "api_key"): "evolink_api_key.txt",
    ("openrouter", "api_key"): "openrouter_api_key.txt",
    ("openai", "api_key"): "openai_api_key.txt",
}

PROVIDER_CONFIG_MAP = {
    "gemini": {
        "model_section": "defaults",
        "api_section": "api_keys",
        "api_key": "google_api_key",
        "api_env": "GOOGLE_API_KEY",
        "vlm_model_section": "gemini",
        "vlm_model_key": "vlm_model",
        "vlm_model_env": "PAPERBANANA_GEMINI_VLM_MODEL",
        "image_model_section": "gemini",
        "image_model_key": "image_model",
        "image_model_env": "PAPERBANANA_GEMINI_IMAGE_MODEL",
        "vlm_api_section": "gemini",
        "vlm_api_key": "vlm_api_key",
        "vlm_api_env": "PAPERBANANA_GEMINI_VLM_API_KEY",
        "image_api_section": "gemini",
        "image_api_key": "image_api_key",
        "image_api_env": "PAPERBANANA_GEMINI_IMAGE_API_KEY",
        "default_model_name": "gemini-3.1-flash-lite-preview",
        "default_image_model_name": "gemini-3.1-flash-image-preview",
        "base_url_section": "gemini",
        "base_url_key": "base_url",
        "base_url_env": "PAPERBANANA_GEMINI_BASE_URL",
        "default_base_url": "",
    },
    "openai": {
        "model_section": "openai",
        "api_section": "openai",
        "api_key": "vlm_api_key",
        "api_env": "PAPERBANANA_OPENAI_VLM_API_KEY",
        "vlm_model_section": "openai",
        "vlm_model_key": "vlm_model",
        "vlm_model_env": "PAPERBANANA_OPENAI_VLM_MODEL",
        "image_model_section": "openai",
        "image_model_key": "image_model",
        "image_model_env": "PAPERBANANA_OPENAI_IMAGE_MODEL",
        "vlm_api_section": "openai",
        "vlm_api_key": "vlm_api_key",
        "vlm_api_env": "PAPERBANANA_OPENAI_VLM_API_KEY",
        "image_api_section": "openai",
        "image_api_key": "image_api_key",
        "image_api_env": "PAPERBANANA_OPENAI_IMAGE_API_KEY",
        "default_model_name": "gpt-5.4-mini",
        "default_image_model_name": "gpt-image-2",
        "base_url_section": "openai",
        "base_url_key": "base_url",
        "base_url_env": "PAPERBANANA_OPENAI_BASE_URL",
        "default_base_url": "https://api.openai.com/v1",
    },
    "evolink": {
        "model_section": "evolink",
        "api_section": "evolink",
        "api_key": "api_key",
        "api_env": "EVOLINK_API_KEY",
        "default_model_name": "gemini-2.5-flash",
        "default_image_model_name": "nano-banana-2-lite",
        "base_url_section": "evolink",
        "base_url_key": "base_url",
        "base_url_env": "EVOLINK_BASE_URL",
        "default_base_url": "https://api.evolink.ai",
    },
    "openrouter": {
        "model_section": "openrouter",
        "api_section": "openrouter",
        "api_key": "api_key",
        "api_env": "OPENROUTER_API_KEY",
        "default_model_name": "google/gemini-3.1-flash-lite-preview",
        "default_image_model_name": "google/gemini-3.1-flash-image-preview",
        "base_url_section": "openrouter",
        "base_url_key": "base_url",
        "base_url_env": "OPENROUTER_BASE_URL",
        "default_base_url": "https://openrouter.ai/api/v1",
    },
}


def _normalize_provider_name(provider: str) -> str:
    return str(provider or "").strip().lower()


def _get_provider_config(provider: str) -> dict[str, str]:
    normalized_provider = _normalize_provider_name(provider)
    provider_config = PROVIDER_CONFIG_MAP.get(normalized_provider)
    if provider_config is None:
        supported = ", ".join(sorted(PROVIDER_CONFIG_MAP))
        raise ValueError(
            f"Unsupported provider: {provider!r}. Expected one of: {supported}."
        )
    return provider_config


def get_repo_root(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir)
    return Path(__file__).resolve().parent.parent


def get_config_dir(base_dir: Path | None = None) -> Path:
    return get_repo_root(base_dir) / CONFIG_DIRNAME


def get_local_secret_dir(base_dir: Path | None = None) -> Path:
    return get_config_dir(base_dir) / LOCAL_SECRET_DIRNAME


def get_local_provider_settings_path(base_dir: Path | None = None) -> Path:
    return get_local_secret_dir(base_dir) / LOCAL_PROVIDER_SETTINGS_FILENAME


def _read_yaml_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    return payload if isinstance(payload, dict) else {}


def read_local_provider_settings(base_dir: Path | None = None) -> dict[str, Any]:
    return _read_yaml_payload(get_local_provider_settings_path(base_dir))


def write_local_provider_settings(
    settings: dict[str, Any],
    base_dir: Path | None = None,
) -> Path:
    settings_path = get_local_provider_settings_path(base_dir)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = settings if isinstance(settings, dict) else {}
    with open(settings_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(normalized, f, allow_unicode=True, sort_keys=False)
    return settings_path


def update_local_provider_settings(
    provider: str,
    values: dict[str, str],
    base_dir: Path | None = None,
) -> Path:
    normalized_provider = _normalize_provider_name(provider)
    settings_path = get_local_provider_settings_path(base_dir)
    if not values:
        return settings_path
    payload = read_local_provider_settings(base_dir)
    provider_payload = dict(payload.get(normalized_provider, {}) or {})
    for key, value in values.items():
        provider_payload[str(key)] = str(value or "").strip()
    updated_payload = dict(payload)
    updated_payload[normalized_provider] = provider_payload
    if updated_payload == payload:
        return settings_path
    payload = updated_payload
    return write_local_provider_settings(payload, base_dir=base_dir)


def _get_local_provider_value(
    provider: str,
    key: str,
    base_dir: Path | None = None,
) -> str:
    payload = read_local_provider_settings(base_dir)
    provider_payload = payload.get(_normalize_provider_name(provider), {})
    if not isinstance(provider_payload, dict):
        return ""
    value = provider_payload.get(key)
    return value.strip() if isinstance(value, str) else ""


def _get_local_provider_value_optional(
    provider: str,
    key: str,
    base_dir: Path | None = None,
) -> str | None:
    payload = read_local_provider_settings(base_dir)
    provider_payload = payload.get(_normalize_provider_name(provider), {})
    if not isinstance(provider_payload, dict) or key not in provider_payload:
        return None
    value = provider_payload.get(key)
    return str(value or "").strip()


def get_local_secret_path(section: str, key: str, base_dir: Path | None = None) -> Path | None:
    filename = SECRET_FILE_MAP.get((section, key))
    if not filename:
        return None
    return get_local_secret_dir(base_dir) / filename


def read_local_secret(section: str, key: str, base_dir: Path | None = None) -> str:
    secret_path = get_local_secret_path(section, key, base_dir=base_dir)
    if not secret_path or not secret_path.exists():
        return ""
    return secret_path.read_text(encoding="utf-8").strip()


def write_local_secret(
    section: str,
    key: str,
    value: str,
    base_dir: Path | None = None,
) -> Path | None:
    secret_path = get_local_secret_path(section, key, base_dir=base_dir)
    if secret_path is None:
        return None

    normalized_value = str(value or "").strip()
    if not normalized_value:
        return secret_path if secret_path.exists() else None

    secret_path.parent.mkdir(parents=True, exist_ok=True)
    current_value = ""
    if secret_path.exists():
        current_value = secret_path.read_text(encoding="utf-8").strip()
    if current_value != normalized_value:
        secret_path.write_text(normalized_value + "\n", encoding="utf-8")
    return secret_path


def delete_local_secret(
    section: str,
    key: str,
    base_dir: Path | None = None,
) -> Path | None:
    secret_path = get_local_secret_path(section, key, base_dir=base_dir)
    if secret_path is None:
        return None
    if secret_path.exists():
        secret_path.unlink()
    return secret_path


def load_model_config(base_dir: Path | None = None) -> dict[str, Any]:
    config_path = get_config_dir(base_dir) / "model_config.yaml"
    if not config_path.exists():
        return {}
    return _read_yaml_payload(config_path)


def get_config_val(
    model_config: dict[str, Any],
    section: str,
    key: str,
    env_var: str,
    default: str = "",
    base_dir: Path | None = None,
    use_env: bool = False,
) -> str:
    if use_env and env_var:
        val = os.getenv(env_var, "").strip()
        if val:
            return val

    val = read_local_secret(section, key, base_dir=base_dir)
    if val:
        return val

    local_settings_value = _get_local_provider_value_optional(section, key, base_dir=base_dir)
    if local_settings_value is not None and (local_settings_value or key == "base_url"):
        return local_settings_value

    if section in model_config:
        val = model_config[section].get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return default


def get_provider_role_base_url(
    provider: str,
    model_config: dict[str, Any],
    base_dir: Path | None = None,
    *,
    image: bool = False,
    use_env: bool = False,
) -> str:
    provider_config = _get_provider_config(provider)
    if not provider_config["base_url_section"]:
        return ""

    role_key = "image_base_url" if image else "vlm_base_url"
    local_role_value = _get_local_provider_value_optional(provider, role_key, base_dir=base_dir)
    if local_role_value is not None:
        return local_role_value

    return get_provider_base_url(
        provider,
        model_config,
        base_dir=base_dir,
        use_env=use_env,
    )


def get_provider_model_defaults(
    provider: str,
    model_config: dict[str, Any],
    base_dir: Path | None = None,
    *,
    use_env: bool = False,
) -> dict[str, str]:
    provider_config = _get_provider_config(provider)
    section_config = model_config.get(provider_config["model_section"], {})
    vlm_section_config = model_config.get(provider_config.get("vlm_model_section", ""), {})
    image_section_config = model_config.get(provider_config.get("image_model_section", ""), {})
    local_vlm_model = _get_local_provider_value(
        provider,
        provider_config.get("vlm_model_key", "model_name"),
        base_dir=base_dir,
    )
    local_image_model = _get_local_provider_value(
        provider,
        provider_config.get("image_model_key", "image_model_name"),
        base_dir=base_dir,
    )
    model_name = (
        local_vlm_model
        or (os.getenv(provider_config.get("vlm_model_env", ""), "").strip() if use_env else "")
        or vlm_section_config.get(provider_config.get("vlm_model_key", ""))
        or section_config.get("model_name")
        or provider_config["default_model_name"]
    )
    image_model_name = (
        local_image_model
        or (os.getenv(provider_config.get("image_model_env", ""), "").strip() if use_env else "")
        or image_section_config.get(provider_config.get("image_model_key", ""))
        or section_config.get("image_model_name")
        or provider_config["default_image_model_name"]
    )
    return {
        "model_name": str(model_name).strip(),
        "image_model_name": str(image_model_name).strip(),
    }


def get_provider_api_key(
    provider: str,
    model_config: dict[str, Any],
    base_dir: Path | None = None,
    *,
    use_env: bool = False,
) -> str:
    provider_config = _get_provider_config(provider)
    val = get_config_val(
        model_config,
        provider_config.get("vlm_api_section", provider_config["api_section"]),
        provider_config.get("vlm_api_key", provider_config["api_key"]),
        provider_config.get("vlm_api_env", provider_config["api_env"]),
        "",
        base_dir=base_dir,
        use_env=use_env,
    )
    if val:
        return val
    return get_config_val(
        model_config,
        provider_config["api_section"],
        provider_config["api_key"],
        provider_config["api_env"],
        "",
        base_dir=base_dir,
        use_env=use_env,
    )


def get_provider_image_api_key(
    provider: str,
    model_config: dict[str, Any],
    base_dir: Path | None = None,
    *,
    use_env: bool = False,
) -> str:
    provider_config = _get_provider_config(provider)
    val = get_config_val(
        model_config,
        provider_config.get("image_api_section", provider_config["api_section"]),
        provider_config.get("image_api_key", provider_config["api_key"]),
        provider_config.get("image_api_env", provider_config["api_env"]),
        "",
        base_dir=base_dir,
        use_env=use_env,
    )
    if val:
        return val
    return get_provider_api_key(provider, model_config, base_dir=base_dir, use_env=use_env)


def get_provider_base_url(
    provider: str,
    model_config: dict[str, Any],
    base_dir: Path | None = None,
    *,
    use_env: bool = False,
) -> str:
    provider_config = _get_provider_config(provider)
    if not provider_config["base_url_section"]:
        return ""
    return get_config_val(
        model_config,
        provider_config["base_url_section"],
        provider_config["base_url_key"],
        provider_config["base_url_env"],
        provider_config["default_base_url"],
        base_dir=base_dir,
        use_env=use_env,
    )


def load_provider_defaults(
    provider: str,
    model_config: dict[str, Any],
    base_dir: Path | None = None,
    *,
    use_env: bool = False,
) -> dict[str, str]:
    defaults = get_provider_model_defaults(provider, model_config, base_dir=base_dir, use_env=use_env)
    defaults["api_key"] = get_provider_api_key(
        provider,
        model_config,
        base_dir=base_dir,
        use_env=use_env,
    )
    defaults["base_url"] = get_provider_base_url(
        provider,
        model_config,
        base_dir=base_dir,
        use_env=use_env,
    )
    defaults["vlm_base_url"] = get_provider_role_base_url(
        provider,
        model_config,
        base_dir=base_dir,
        image=False,
        use_env=use_env,
    )
    defaults["image_base_url"] = get_provider_role_base_url(
        provider,
        model_config,
        base_dir=base_dir,
        image=True,
        use_env=use_env,
    )
    return defaults


def write_provider_runtime_defaults(
    provider: str,
    *,
    base_url: str | None = None,
    model_name: str | None = None,
    image_model_name: str | None = None,
    base_url_role: str = "shared",
    base_dir: Path | None = None,
) -> Path:
    provider_config = _get_provider_config(provider)
    values = {}
    if base_url is not None:
        normalized_role = str(base_url_role or "shared").strip().lower()
        if normalized_role == "vlm":
            values["vlm_base_url"] = base_url
        elif normalized_role == "image":
            values["image_base_url"] = base_url
        else:
            values[provider_config["base_url_key"]] = base_url
    if model_name is not None:
        values[provider_config.get("vlm_model_key", "model_name")] = model_name
    if image_model_name is not None:
        values[provider_config.get("image_model_key", "image_model_name")] = image_model_name
    return update_local_provider_settings(provider, values, base_dir=base_dir)


def write_provider_api_key(
    provider: str,
    api_key: str,
    base_dir: Path | None = None,
) -> Path | None:
    provider_config = _get_provider_config(provider)
    return write_local_secret(
        provider_config.get("vlm_api_section", provider_config["api_section"]),
        provider_config.get("vlm_api_key", provider_config["api_key"]),
        api_key,
        base_dir=base_dir,
    )


def delete_provider_api_key(
    provider: str,
    base_dir: Path | None = None,
) -> Path | None:
    provider_config = _get_provider_config(provider)
    return delete_local_secret(
        provider_config.get("vlm_api_section", provider_config["api_section"]),
        provider_config.get("vlm_api_key", provider_config["api_key"]),
        base_dir=base_dir,
    )


def write_provider_image_api_key(
    provider: str,
    api_key: str,
    base_dir: Path | None = None,
) -> Path | None:
    provider_config = _get_provider_config(provider)
    return write_local_secret(
        provider_config.get("image_api_section", provider_config["api_section"]),
        provider_config.get("image_api_key", provider_config["api_key"]),
        api_key,
        base_dir=base_dir,
    )


def delete_provider_image_api_key(
    provider: str,
    base_dir: Path | None = None,
) -> Path | None:
    provider_config = _get_provider_config(provider)
    return delete_local_secret(
        provider_config.get("image_api_section", provider_config["api_section"]),
        provider_config.get("image_api_key", provider_config["api_key"]),
        base_dir=base_dir,
    )
