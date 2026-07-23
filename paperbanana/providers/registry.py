"""Provider registry and factory for PaperBanana."""

from __future__ import annotations

import structlog
from pydantic import SecretStr

from paperbanana.core.config import Settings
from paperbanana.providers.base import ImageGenProvider, VLMProvider

logger = structlog.get_logger()


_API_KEY_HINTS = {
    "GOOGLE_API_KEY": (
        "GOOGLE_API_KEY not found.\n\n"
        "To fix this:\n"
        "  1. Get a free API key at: https://makersuite.google.com/app/apikey\n"
        "  2. Run: paperbanana setup\n\n"
        "Or set it manually:\n"
        "  export GOOGLE_API_KEY=your-key-here"
    ),
    "OPENROUTER_API_KEY": (
        "OPENROUTER_API_KEY not found.\n\n"
        "To fix this:\n"
        "  1. Get an API key at: https://openrouter.ai/keys\n"
        "  2. Set the environment variable:\n\n"
        "  export OPENROUTER_API_KEY=your-key-here"
    ),
    "OPENAI_API_KEY": (
        "OPENAI_API_KEY not found.\n\n"
        "To fix this:\n"
        "  1. Get an API key at: https://platform.openai.com/api-keys\n"
        "  2. Set the environment variable:\n\n"
        "  export OPENAI_API_KEY=your-key-here"
    ),
    "ATLASCLOUD_API_KEY": (
        "ATLASCLOUD_API_KEY not found.\n\n"
        "To fix this:\n"
        "  1. Get an API key at: "
        "https://www.atlascloud.ai/console/api-keys?utm_source=github&utm_medium=link&utm_campaign=paperbanana\n"
        "  2. Set the environment variable:\n\n"
        "  export ATLASCLOUD_API_KEY=your-key-here"
    ),
    "ANTHROPIC_API_KEY": (
        "ANTHROPIC_API_KEY not found.\n\n"
        "To fix this:\n"
        "  1. Get an API key at: https://console.anthropic.com/settings/keys\n"
        "  2. Set the environment variable:\n\n"
        "  export ANTHROPIC_API_KEY=your-key-here"
    ),
    "AWS_CREDENTIALS": (
        "AWS credentials not found for Bedrock.\n\n"
        "To fix this, configure one of:\n"
        "  1. Environment variables:\n"
        "     export AWS_ACCESS_KEY_ID=your-key\n"
        "     export AWS_SECRET_ACCESS_KEY=your-secret\n\n"
        "  2. AWS credentials file (~/.aws/credentials):\n"
        "     aws configure\n\n"
        "  3. IAM role (for EC2/ECS/Lambda)"
    ),
}


def _validate_api_key(key_value: str | None, env_var_name: str) -> None:
    """Raise a helpful error if the required API key is missing."""
    if key_value is None or not key_value.strip():
        hint = _API_KEY_HINTS.get(env_var_name, f"{env_var_name} is not set.")
        raise ValueError(hint)


def _secret_value(value: SecretStr | str | None) -> str | None:
    """Unwrap a runtime secret only at the provider construction boundary."""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


def _role_api_key(settings: Settings, role: str, legacy_value: str | None) -> str | None:
    if settings.connection_source == "profiles":
        return _secret_value(getattr(settings, f"{role}_api_key"))
    return legacy_value


def _role_base_url(settings: Settings, role: str, legacy_value: str | None) -> str | None:
    if settings.connection_source == "profiles":
        return getattr(settings, f"{role}_base_url")
    return legacy_value


def _key_label(settings: Settings, role: str, legacy_name: str) -> str:
    if settings.connection_source == "profiles":
        return f"{role.upper()}_API_KEY"
    return legacy_name


def _validate_bedrock_auth(region: str, profile: str | None) -> None:
    """Raise a helpful error if AWS credentials are not available."""
    try:
        import boto3
    except ImportError:
        raise ImportError(
            "boto3 is required for the Bedrock provider. "
            "Install with: pip install 'paperbanana[bedrock]'"
        )
    session = boto3.Session(region_name=region, profile_name=profile)
    credentials = session.get_credentials()
    if credentials is None:
        raise ValueError(_API_KEY_HINTS["AWS_CREDENTIALS"])


class ProviderRegistry:
    """Factory for creating VLM and image generation providers from config."""

    @staticmethod
    def create_vlm(settings: Settings) -> VLMProvider:
        """Create a VLM provider based on settings."""
        provider = settings.vlm_provider.lower()
        logger.info("Creating VLM provider", provider=provider, model=settings.effective_vlm_model)

        if provider == "gemini":
            api_key = _role_api_key(settings, "vlm", settings.google_api_key)
            _validate_api_key(api_key, _key_label(settings, "vlm", "GOOGLE_API_KEY"))
            from paperbanana.providers.vlm.gemini import GeminiVLM

            return GeminiVLM(
                api_key=api_key,
                model=settings.effective_vlm_model,
                base_url=_role_base_url(settings, "vlm", settings.google_base_url),
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "openrouter":
            api_key = _role_api_key(settings, "vlm", settings.openrouter_api_key)
            _validate_api_key(api_key, _key_label(settings, "vlm", "OPENROUTER_API_KEY"))
            from paperbanana.providers.vlm.openrouter import OpenRouterVLM

            return OpenRouterVLM(
                api_key=api_key,
                model=settings.effective_vlm_model,
                base_url=_role_base_url(settings, "vlm", "https://openrouter.ai/api/v1")
                or "https://openrouter.ai/api/v1",
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "openai":
            api_key = _role_api_key(settings, "vlm", settings.openai_api_key)
            _validate_api_key(api_key, _key_label(settings, "vlm", "OPENAI_API_KEY"))
            from paperbanana.providers.vlm.openai import OpenAIVLM

            return OpenAIVLM(
                api_key=api_key,
                model=settings.effective_vlm_model,
                base_url=_role_base_url(settings, "vlm", settings.openai_base_url)
                or "https://api.openai.com/v1",
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "atlas":
            api_key = _role_api_key(settings, "vlm", settings.atlascloud_api_key)
            _validate_api_key(api_key, _key_label(settings, "vlm", "ATLASCLOUD_API_KEY"))
            from paperbanana.providers.vlm.atlas import AtlasVLM

            return AtlasVLM(
                api_key=api_key,
                model=settings.effective_vlm_model,
                base_url=_role_base_url(settings, "vlm", settings.atlascloud_base_url)
                or "https://api.atlascloud.ai/v1",
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "bedrock":
            _validate_bedrock_auth(settings.aws_region, settings.aws_profile)
            from paperbanana.providers.vlm.bedrock import BedrockVLM

            return BedrockVLM(
                model=settings.effective_vlm_model,
                region=settings.aws_region,
                profile=settings.aws_profile,
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "anthropic":
            api_key = _role_api_key(settings, "vlm", settings.anthropic_api_key)
            _validate_api_key(api_key, _key_label(settings, "vlm", "ANTHROPIC_API_KEY"))
            from paperbanana.providers.vlm.anthropic import AnthropicVLM

            return AnthropicVLM(
                api_key=api_key,
                model=settings.effective_vlm_model,
                base_url=_role_base_url(settings, "vlm", None),
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "ollama":
            from paperbanana.providers.vlm.ollama import OllamaVLM

            return OllamaVLM(
                model=settings.effective_vlm_model,
                base_url=_role_base_url(settings, "vlm", settings.ollama_base_url)
                or "http://localhost:11434/v1",
                json_mode=settings.ollama_json_mode,
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "openai_local":
            from paperbanana.providers.vlm.openai import OpenAIVLM

            return OpenAIVLM(
                api_key=_role_api_key(settings, "vlm", settings.openai_api_key) or "not-needed",
                model=settings.effective_vlm_model,
                base_url=_role_base_url(settings, "vlm", settings.openai_local_base_url),
                json_mode=settings.openai_local_json_mode,
                provider_name="openai_local",
                timeout_seconds=settings.vlm_timeout_seconds,
            )
        elif provider == "claude_code":
            from paperbanana.providers.vlm.claude_code import ClaudeCodeVLM

            vlm = ClaudeCodeVLM(
                model=settings.effective_vlm_model,
                timeout_seconds=settings.vlm_timeout_seconds,
            )
            if not vlm.is_available():
                raise ValueError(
                    "claude CLI not found in PATH.\n\n"
                    "Install Claude Code and sign in, then"
                    " ensure `claude` is available on PATH."
                )
            return vlm
        elif provider == "litellm":
            from paperbanana.providers.vlm.litellm import LiteLLMVLM

            vlm = LiteLLMVLM(
                model=settings.effective_vlm_model,
                api_key=_role_api_key(settings, "vlm", settings.litellm_api_key),
                api_base=_role_base_url(settings, "vlm", settings.litellm_api_base),
                timeout_seconds=settings.vlm_timeout_seconds,
            )
            if not vlm.is_available():
                raise ImportError(
                    "litellm is required for the LiteLLM provider. "
                    "Install with: pip install 'paperbanana[litellm]'"
                )
            return vlm
        else:
            raise ValueError(
                "Unknown VLM provider: "
                f"{provider}. Available: gemini, openrouter, openai, atlas, openai_local, "
                f"bedrock, anthropic, ollama, claude_code, litellm"
            )

    @staticmethod
    def create_image_gen(
        settings: Settings, *, validate_credentials: bool = True
    ) -> ImageGenProvider:
        """Create an image generation provider based on settings."""
        provider = settings.image_provider.lower()
        logger.info(
            "Creating image gen provider",
            provider=provider,
            model=settings.effective_image_model,
        )

        if provider == "none":
            from paperbanana.providers.image_gen.dummy import DummyImageGen

            return DummyImageGen()
        elif provider == "google_imagen":
            api_key = _role_api_key(settings, "image", settings.google_api_key)
            if validate_credentials:
                _validate_api_key(api_key, _key_label(settings, "image", "GOOGLE_API_KEY"))
            from paperbanana.providers.image_gen.google_imagen import GoogleImagenGen

            return GoogleImagenGen(
                api_key=api_key,
                model=settings.effective_image_model,
                base_url=_role_base_url(settings, "image", settings.google_base_url),
                timeout_seconds=settings.image_timeout_seconds,
            )
        elif provider == "openrouter_imagen":
            api_key = _role_api_key(settings, "image", settings.openrouter_api_key)
            if validate_credentials:
                _validate_api_key(api_key, _key_label(settings, "image", "OPENROUTER_API_KEY"))
            from paperbanana.providers.image_gen.openrouter_imagen import (
                OpenRouterImageGen,
            )

            return OpenRouterImageGen(
                api_key=api_key,
                model=settings.effective_image_model,
                base_url=_role_base_url(settings, "image", "https://openrouter.ai/api/v1")
                or "https://openrouter.ai/api/v1",
                timeout_seconds=settings.image_timeout_seconds,
            )
        elif provider == "openai_imagen":
            api_key = _role_api_key(settings, "image", settings.openai_api_key)
            if validate_credentials:
                _validate_api_key(api_key, _key_label(settings, "image", "OPENAI_API_KEY"))
            from paperbanana.providers.image_gen.openai_imagen import OpenAIImageGen

            return OpenAIImageGen(
                api_key=api_key,
                model=settings.effective_image_model,
                base_url=_role_base_url(settings, "image", settings.openai_base_url)
                or "https://api.openai.com/v1",
                size_mode=settings.image_size_mode or "fixed",
                timeout_seconds=settings.image_timeout_seconds,
            )
        elif provider == "atlas_imagen":
            api_key = _role_api_key(settings, "image", settings.atlascloud_api_key)
            if validate_credentials:
                _validate_api_key(api_key, _key_label(settings, "image", "ATLASCLOUD_API_KEY"))
            from paperbanana.providers.image_gen.atlas_imagen import AtlasImageGen

            return AtlasImageGen(
                api_key=api_key,
                model=settings.effective_image_model,
                base_url=_role_base_url(settings, "image", settings.atlascloud_image_base_url)
                or "https://api.atlascloud.ai/api/v1",
                timeout_seconds=settings.image_timeout_seconds,
            )
        elif provider == "bedrock_imagen":
            if validate_credentials:
                _validate_bedrock_auth(settings.aws_region, settings.aws_profile)
            from paperbanana.providers.image_gen.bedrock_imagen import BedrockImageGen

            return BedrockImageGen(
                model=settings.effective_image_model,
                region=settings.aws_region,
                profile=settings.aws_profile,
                timeout_seconds=settings.image_timeout_seconds,
            )
        else:
            raise ValueError(
                f"Unknown image provider: {provider}. "
                "Available: none, google_imagen, openrouter_imagen, "
                "openai_imagen, atlas_imagen, bedrock_imagen"
            )
