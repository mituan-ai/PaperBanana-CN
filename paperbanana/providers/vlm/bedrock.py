"""AWS Bedrock VLM provider using the Converse API."""

from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Optional

import structlog
from PIL import Image
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from paperbanana.providers.base import VLMProvider, is_retryable_provider_error

logger = structlog.get_logger()


class BedrockVLM(VLMProvider):
    """VLM provider using the AWS Bedrock Converse API.

    Supports Claude, Nova, and other models available through Bedrock.
    Authenticates via the standard boto3 credential chain
    (env vars, ~/.aws/credentials, IAM role).
    """

    def __init__(
        self,
        model: str = "us.amazon.nova-pro-v1:0",
        region: str = "us-east-1",
        profile: Optional[str] = None,
        timeout_seconds: float = 180.0,
    ):
        self._model = model
        self._region = region
        self._profile = profile
        self._timeout_seconds = timeout_seconds
        self._client = None

    @property
    def name(self) -> str:
        return "bedrock"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError(
                    "boto3 is required for the Bedrock provider. "
                    "Install with: pip install 'paperbanana[bedrock]'"
                )
            session = boto3.Session(
                region_name=self._region,
                profile_name=self._profile,
            )
            client_kwargs = {}
            try:
                from botocore.config import Config

                client_kwargs["config"] = Config(
                    connect_timeout=self._timeout_seconds,
                    read_timeout=self._timeout_seconds,
                )
            except ImportError:
                # Lightweight test stubs may provide boto3 without botocore.
                pass
            self._client = session.client("bedrock-runtime", **client_kwargs)
        return self._client

    def is_available(self) -> bool:
        try:
            import boto3
        except ImportError:
            return False
        session = boto3.Session(
            region_name=self._region,
            profile_name=self._profile,
        )
        credentials = session.get_credentials()
        return credentials is not None

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

        content = []
        if images:
            for img in images:
                buf = BytesIO()
                img.save(buf, format="PNG")
                content.append(
                    {
                        "image": {
                            "format": "png",
                            "source": {"bytes": buf.getvalue()},
                        }
                    }
                )
        content.append({"text": prompt})

        kwargs: dict = {
            "modelId": self._model,
            "messages": [{"role": "user", "content": content}],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
            },
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: client.converse(**kwargs))

        text = response["output"]["message"]["content"][0]["text"]

        usage = response.get("usage")
        logger.debug("Bedrock response", model=self._model, usage=usage)

        if self.cost_tracker is not None and usage:
            self.cost_tracker.record_vlm_call(
                provider=self.name,
                model=self._model,
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
            )
        return text
