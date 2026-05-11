import asyncio
import unittest
from unittest.mock import patch

from utils import generation_utils


class _DummyPart:
    def __init__(self, text: str):
        self.text = text


class _DummyContent:
    def __init__(self, text: str):
        self.parts = [_DummyPart(text)]


class _DummyCandidate:
    def __init__(self, text: str):
        self.content = _DummyContent(text)


class _DummyResponse:
    def __init__(self, text: str):
        self.candidates = [_DummyCandidate(text)]


class _DummyModels:
    def __init__(self, text: str, delay: float = 0.0):
        self.text = text
        self.delay = delay

    async def generate_content(self, **kwargs):
        await asyncio.sleep(self.delay)
        return _DummyResponse(self.text)


class _DummyGeminiClient:
    def __init__(self, text: str, delay: float = 0.0):
        self.aio = type("DummyAio", (), {"models": _DummyModels(text, delay)})()


class _DummyConfig:
    def __init__(self, candidate_count=1):
        self.candidate_count = candidate_count
        self.response_modalities = None


class _DummyEvolinkProvider:
    def __init__(self):
        self.close_calls = 0

    async def close(self):
        self.close_calls += 1


class GenerationUtilsRuntimeContextTest(unittest.TestCase):
    def test_concurrent_runtime_contexts_use_isolated_clients_and_hooks(self):
        hook_events_a = []
        hook_events_b = []
        context_a = generation_utils.RuntimeContext(
            provider="gemini",
            api_key="key-a",
            event_hook=hook_events_a.append,
            gemini_client=_DummyGeminiClient("result-a", delay=0.02),
        )
        context_b = generation_utils.RuntimeContext(
            provider="gemini",
            api_key="key-b",
            event_hook=hook_events_b.append,
            gemini_client=_DummyGeminiClient("result-b", delay=0.0),
        )

        async def run_with_context(context, model_name):
            with generation_utils.use_runtime_context(context):
                return await generation_utils.call_gemini_with_retry_async(
                    model_name=model_name,
                    contents=[{"type": "text", "text": "hello"}],
                    config=_DummyConfig(),
                    max_attempts=1,
                    retry_delay=0,
                    error_context=f"context={model_name}",
                )

        async def run_both():
            return await asyncio.gather(
                run_with_context(context_a, "model-a"),
                run_with_context(context_b, "model-b"),
            )

        results = asyncio.run(run_both())

        self.assertEqual(results, [["result-a"], ["result-b"]])
        self.assertTrue(any(event.get("model") == "model-a" for event in hook_events_a))
        self.assertTrue(any(event.get("model") == "model-b" for event in hook_events_b))
        self.assertFalse(any(event.get("model") == "model-b" for event in hook_events_a))
        self.assertFalse(any(event.get("model") == "model-a" for event in hook_events_b))

    def test_close_runtime_context_only_closes_owned_provider(self):
        provider = _DummyEvolinkProvider()
        context = generation_utils.RuntimeContext(
            provider="evolink",
            api_key="key",
            evolink_provider=provider,
            owns_evolink_provider=True,
        )

        asyncio.run(generation_utils.close_runtime_context(context))

        self.assertEqual(provider.close_calls, 1)

    def test_gemini_retry_handles_none_candidate_count(self):
        context = generation_utils.RuntimeContext(
            provider="gemini",
            api_key="key-a",
            gemini_client=_DummyGeminiClient("result-a", delay=0.0),
        )

        async def run_once():
            with generation_utils.use_runtime_context(context):
                return await generation_utils.call_gemini_with_retry_async(
                    model_name="model-a",
                    contents=[{"type": "text", "text": "hello"}],
                    config=_DummyConfig(candidate_count=None),
                    max_attempts=1,
                    retry_delay=0,
                    error_context="candidate-count-none",
                )

        results = asyncio.run(run_once())

        self.assertEqual(results, ["result-a"])

    def test_close_runtime_context_skips_unowned_provider(self):
        provider = _DummyEvolinkProvider()
        context = generation_utils.RuntimeContext(
            provider="evolink",
            api_key="key",
            evolink_provider=provider,
            owns_evolink_provider=False,
        )

        asyncio.run(generation_utils.close_runtime_context(context))

        self.assertEqual(provider.close_calls, 0)

    def test_apiyi_image_url_normalizes_to_http_long_connection_endpoint(self):
        self.assertEqual(
            generation_utils._normalize_apiyi_image_base_url("https://api.apiyi.com/v1"),
            "http://api.apiyi.com:16888/v1",
        )
        self.assertEqual(
            generation_utils._normalize_apiyi_image_base_url("https://api.apiyi.com"),
            "http://api.apiyi.com:16888/v1",
        )

    def test_apiyi_image_client_uses_custom_httpx_without_affecting_text_client(self):
        calls = []

        class _FakeAsyncOpenAI:
            def __init__(self, **kwargs):
                calls.append(kwargs)

        class _FakeHttpClient:
            pass

        with patch("openai.AsyncOpenAI", _FakeAsyncOpenAI):
            with patch(
                "utils.generation_utils._create_openai_http_client_for_apiyi_image",
                return_value=_FakeHttpClient(),
            ):
                generation_utils.create_runtime_context(
                    provider="openai",
                    api_key="text-key",
                    image_api_key="image-key",
                    image_model_name="gpt-image-2-vip",
                    base_url="https://api.openai.com/v1",
                    image_base_url="",
                )

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["base_url"], "https://api.openai.com/v1")
        self.assertNotIn("http_client", calls[0])
        self.assertEqual(calls[1]["base_url"], "http://api.apiyi.com:16888/v1")
        self.assertIn("http_client", calls[1])
        self.assertEqual(calls[1]["timeout"], generation_utils.DEFAULT_APIYI_IMAGE_TIMEOUT_SECONDS)

    def test_explicit_image_base_url_is_preserved_even_for_apiyi_label(self):
        calls = []

        class _FakeAsyncOpenAI:
            def __init__(self, **kwargs):
                calls.append(kwargs)

        with patch("openai.AsyncOpenAI", _FakeAsyncOpenAI):
            generation_utils.create_runtime_context(
                provider="openai",
                api_key="text-key",
                image_api_key="image-key",
                image_model_name="gpt-image-2-vip(apiyi)",
                base_url="https://api.openai.com/v1",
                image_base_url="https://image.example/v1",
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["base_url"], "https://image.example/v1")
        self.assertNotIn("http_client", calls[1])
        self.assertEqual(calls[1].get("timeout"), None)

    def test_reinitialize_runtime_context_keeps_text_and_image_urls_separate(self):
        calls = []

        def fake_create_openai_client(api_key, base_url="", extra_headers=None, *, image_client=False):
            calls.append(
                {
                    "api_key": api_key,
                    "base_url": base_url,
                    "extra_headers": extra_headers,
                    "image_client": image_client,
                }
            )
            return f"client-{len(calls)}"

        context = generation_utils.RuntimeContext(
            provider="openai",
            api_key="text-key",
            base_url="https://text.example/v1",
            image_provider="openai",
            image_api_key="image-key",
            image_base_url="https://image.example/v1",
            extra_headers={"X-Text": "1"},
            image_extra_headers={"X-Image": "1"},
        )

        with patch("utils.generation_utils._create_openai_client", side_effect=fake_create_openai_client):
            generation_utils.reinitialize_runtime_context(context)

        self.assertEqual(calls[0]["api_key"], "text-key")
        self.assertEqual(calls[0]["base_url"], "https://text.example/v1")
        self.assertEqual(calls[0]["extra_headers"], {"X-Text": "1"})
        self.assertFalse(calls[0]["image_client"])
        self.assertEqual(calls[1]["api_key"], "image-key")
        self.assertEqual(calls[1]["base_url"], "https://image.example/v1")
        self.assertEqual(calls[1]["extra_headers"], {"X-Image": "1"})
        self.assertTrue(calls[1]["image_client"])
        self.assertEqual(context.openai_client, "client-1")
        self.assertEqual(context.openai_image_client, "client-2")

    def test_create_runtime_context_does_not_build_gemini_image_client_for_non_gemini_image_provider(self):
        gemini_calls = []
        openai_calls = []

        def fake_create_gemini_client(api_key, base_url=""):
            gemini_calls.append({"api_key": api_key, "base_url": base_url})
            return f"gemini-{len(gemini_calls)}"

        def fake_create_openai_client(api_key, base_url="", extra_headers=None, *, image_client=False):
            openai_calls.append(
                {
                    "api_key": api_key,
                    "base_url": base_url,
                    "extra_headers": extra_headers,
                    "image_client": image_client,
                }
            )
            return f"openai-{len(openai_calls)}"

        with patch("utils.generation_utils._create_gemini_client", side_effect=fake_create_gemini_client):
            with patch("utils.generation_utils._create_openai_client", side_effect=fake_create_openai_client):
                context = generation_utils.create_runtime_context(
                    provider="gemini",
                    api_key="text-key",
                    base_url="https://text.example/v1",
                    image_provider="openai",
                    image_api_key="image-key",
                    image_base_url="https://image.example/v1",
                )

        self.assertEqual(gemini_calls, [{"api_key": "text-key", "base_url": "https://text.example/v1"}])
        self.assertEqual(openai_calls[0]["api_key"], "image-key")
        self.assertEqual(openai_calls[0]["base_url"], "https://image.example/v1")
        self.assertTrue(openai_calls[0]["image_client"])
        self.assertEqual(context.gemini_client, "gemini-1")
        self.assertIsNone(context.gemini_image_client)
        self.assertEqual(context.openai_image_client, "openai-1")


if __name__ == "__main__":
    unittest.main()
