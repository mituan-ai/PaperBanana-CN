"""OpenAI image generation provider — works with both OpenAI and Azure OpenAI endpoints."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional, Sequence

import structlog
from PIL import Image
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from paperbanana_cn.core.config import OUTPUT_RESOLUTION_VALUES
from paperbanana_cn.core.types import ASPECT_RATIO_VALUES
from paperbanana_cn.providers.base import (
    ImageGenProvider,
    ImageSizeMode,
    is_retryable_provider_error,
)

logger = structlog.get_logger()


class OpenAIImageGen(ImageGenProvider):
    """Image generation using the OpenAI Python SDK (async).

    Supports GPT-Image-1.5, GPT-Image-1, DALL-E 3, and other OpenAI image models.
    Compatible with both OpenAI and Azure OpenAI / Foundry endpoints.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-image-1.5",
        base_url: str = "https://api.openai.com/v1",
        size_mode: ImageSizeMode | str = ImageSizeMode.FIXED,
        supported_ratios: Sequence[str] | None = None,
        supported_resolutions: Sequence[str] | None = None,
        timeout_seconds: float = 180.0,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._size_mode = ImageSizeMode(size_mode)
        default_ratios = (
            ASPECT_RATIO_VALUES
            if self._size_mode == ImageSizeMode.EXPLICIT_PIXELS
            else (
                "1:1",
                "3:2",
                "2:3",
            )
        )
        default_resolutions = (
            OUTPUT_RESOLUTION_VALUES
            if self._size_mode == ImageSizeMode.EXPLICIT_PIXELS
            else ("1k",)
        )
        self._supported_ratios = list(supported_ratios or default_ratios)
        self._supported_resolutions = list(supported_resolutions or default_resolutions)
        self._timeout_seconds = timeout_seconds
        self._client = None

    @property
    def name(self) -> str:
        return "openai_imagen"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    timeout=self._timeout_seconds,
                )
            except ImportError:
                raise ImportError(
                    "openai is required for the OpenAI provider. "
                    "Install with: pip install --upgrade paperbanana-cn"
                )
        return self._client

    def is_available(self) -> bool:
        return self._api_key is not None

    @property
    def supported_ratios(self) -> list[str]:
        return list(self._supported_ratios)

    @property
    def supported_resolutions(self) -> list[str]:
        return list(self._supported_resolutions)

    @property
    def size_mode(self) -> ImageSizeMode:
        return self._size_mode

    def _size_string(self, width: int, height: int) -> str:
        """Map pixel dimensions to an OpenAI-supported size string."""
        if self._size_mode == ImageSizeMode.EXPLICIT_PIXELS:
            return f"{width}x{height}"
        ratio = width / height
        if ratio > 1.2:
            return "1536x1024"
        if ratio < 0.83:
            return "1024x1536"
        return "1024x1024"

    # Fixed-size OpenAI image protocols expose these exact native ratios.
    _RATIO_TO_SIZE = {
        "3:2": "1536x1024",
        "1:1": "1024x1024",
        "2:3": "1024x1536",
    }

    def requested_size_label(
        self, aspect_ratio: str, resolution: str, width: int, height: int
    ) -> str:
        self.validate_output_options(aspect_ratio, resolution)
        if self._size_mode == ImageSizeMode.EXPLICIT_PIXELS:
            return f"{width}x{height} px"
        return self._RATIO_TO_SIZE[aspect_ratio] + " px"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=30),
        retry=retry_if_exception(is_retryable_provider_error),
    )
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
        client = self._get_client()

        full_prompt = prompt
        if negative_prompt:
            full_prompt += f"\n\nAvoid: {negative_prompt}"

        if self._size_mode == ImageSizeMode.EXPLICIT_PIXELS:
            size = self._size_string(width, height)
        else:
            size = self._RATIO_TO_SIZE.get(aspect_ratio or "", self._size_string(width, height))

        kwargs = {
            "model": self._model,
            "prompt": full_prompt,
            "n": 1,
            "size": size,
        }
        if quality:
            kwargs["quality"] = quality

        result = await client.images.generate(**kwargs)

        b64_data = result.data[0].b64_json
        image_bytes = base64.b64decode(b64_data)

        if self.cost_tracker is not None:
            self.cost_tracker.record_image_call(provider=self.name, model=self._model)
        return Image.open(BytesIO(image_bytes))
