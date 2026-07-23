"""Abstract base classes for all providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Optional

from PIL import Image

if TYPE_CHECKING:
    from paperbanana.core.cost_tracker import CostTracker


class ImageSizeMode(str, Enum):
    """How an image provider consumes requested output dimensions."""

    EXPLICIT_PIXELS = "explicit_pixels"
    NATIVE_TIER = "native_tier"
    FIXED = "fixed"
    PROMPT_HINT = "prompt_hint"


def is_retryable_provider_error(error: BaseException) -> bool:
    """Retry only transport failures, throttling, and server-side errors."""
    status_code = getattr(error, "status_code", None)
    if not isinstance(status_code, int):
        status_code = getattr(getattr(error, "response", None), "status_code", None)
    if isinstance(status_code, int):
        return status_code in {408, 409, 425, 429} or status_code >= 500
    name = type(error).__name__.lower()
    if any(
        token in name
        for token in ("timeout", "connection", "ratelimit", "throttl", "serviceunavailable")
    ):
        return True
    return isinstance(error, OSError)


class VLMProvider(ABC):
    """Abstract interface for Vision-Language Model providers.

    All VLM providers (used by Retriever, Planner, Stylist, Critic agents)
    must implement this interface.
    """

    cost_tracker: CostTracker | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and config."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier being used."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        images: Optional[list[Image.Image]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate text from a prompt, optionally with images.

        Args:
            prompt: The user prompt text.
            images: Optional list of images for vision tasks.
            system_prompt: Optional system-level instructions.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens in the response.
            response_format: Optional format hint ("json" for JSON mode).

        Returns:
            Generated text response.
        """
        ...

    @property
    def supports_json_mode(self) -> bool:
        """Whether this provider reliably handles response_format='json'."""
        return True

    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        return True


class ImageGenProvider(ABC):
    """Abstract interface for image generation providers.

    Used by the Visualizer agent to generate methodology diagrams
    and other academic illustrations.

    Providers explicitly declare ratios, resolutions, sizing behavior, and
    guided-edit support. Callers must validate these capabilities before a
    paid generation request.
    """

    cost_tracker: CostTracker | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and config."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier being used."""
        ...

    @property
    def supported_ratios(self) -> list[str]:
        """Aspect ratios this provider supports. Override in subclasses."""
        return ["1:1", "16:9"]  # conservative default

    @property
    def supported_resolutions(self) -> list[str]:
        """Resolution tiers this provider accepts."""
        return ["1k"]

    @property
    def size_mode(self) -> ImageSizeMode:
        """How width, height, and resolution are represented on the wire."""
        return ImageSizeMode.FIXED

    @property
    def supports_image_edit(self) -> bool:
        """Whether ``generate`` accepts source images for guided editing."""
        return False

    def validate_output_options(self, aspect_ratio: str, resolution: str) -> None:
        """Reject unsupported options before starting a paid request."""
        if aspect_ratio not in self.supported_ratios:
            raise ValueError(
                f"Image provider '{self.name}' does not support aspect ratio {aspect_ratio}. "
                f"Supported: {', '.join(self.supported_ratios)}"
            )
        normalized_resolution = resolution.lower()
        if normalized_resolution not in self.supported_resolutions:
            raise ValueError(
                f"Image provider '{self.name}' does not support resolution {resolution.upper()}. "
                f"Supported: {', '.join(item.upper() for item in self.supported_resolutions)}"
            )

    def requested_size_label(
        self,
        aspect_ratio: str,
        resolution: str,
        width: int,
        height: int,
    ) -> str:
        """Describe the exact pixels or native tier sent to this provider."""
        self.validate_output_options(aspect_ratio, resolution)
        if self.size_mode == ImageSizeMode.EXPLICIT_PIXELS:
            return f"{width}x{height} px"
        if self.size_mode == ImageSizeMode.NATIVE_TIER:
            return f"{aspect_ratio} / {resolution.upper()} native tier"
        if self.size_mode == ImageSizeMode.PROMPT_HINT:
            return f"{aspect_ratio} prompt hint / {resolution.upper()}"
        return f"{aspect_ratio} provider preset"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> Image.Image:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the desired image.
            negative_prompt: What to avoid in the image.
            width: Output image width in pixels.
            height: Output image height in pixels.
            seed: Random seed for reproducibility.
            aspect_ratio: Target aspect ratio from ``SUPPORTED_ASPECT_RATIOS``.
                takes precedence over width/height for providers that support it.
            quality: Optional provider-specific rendering quality.

        Returns:
            Generated PIL Image.
        """
        ...

    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        return True
