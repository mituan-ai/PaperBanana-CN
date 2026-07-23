"""OpenRouter VLM provider — OpenAI-compatible API for any model."""

from __future__ import annotations

from typing import Optional

import structlog
from PIL import Image
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from paperbanana_cn.core.utils import image_to_base64
from paperbanana_cn.providers.base import VLMProvider, is_retryable_provider_error

logger = structlog.get_logger()


class OpenRouterVLM(VLMProvider):
    """VLM provider that routes through OpenRouter's OpenAI-compatible API.

    Works with any model on OpenRouter (Gemini, Claude, GPT, Llama, etc.).
    Get an API key at https://openrouter.ai/keys
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "google/gemini-3-flash-preview",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 120.0,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = None

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        """Lazy-init an async httpx client pointed at the OpenRouter API."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "HTTP-Referer": "https://github.com/llmsresearch/paperbanana",
                    "X-Title": "PaperBanana",
                },
                timeout=self._timeout_seconds,
            )
        return self._client

    def is_available(self) -> bool:
        return self._api_key is not None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=30),
        retry=retry_if_exception(is_retryable_provider_error),
    )
    async def generate(
        self,
        prompt: str,
        images: Optional[list[Image.Image]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> str:
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Build multimodal content array (vision images + text)
        content = []
        if images:
            for img in images:
                b64 = image_to_base64(img)
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    }
                )
        content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": content})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()
        text = data["choices"][0]["message"]["content"]

        usage = data.get("usage")
        logger.debug("OpenRouter response", model=self._model, usage=usage)

        if self.cost_tracker is not None and usage:
            self.cost_tracker.record_vlm_call(
                provider=self.name,
                model=self._model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )
        return text
