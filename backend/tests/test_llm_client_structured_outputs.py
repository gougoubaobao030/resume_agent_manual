import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from pydantic import BaseModel, Field

from clients import llm_client as llm_client_module
from clients.llm_client import LLMClient, LLMConfigError, LLMRequestError, LLMResponseError
from openai import APIConnectionError, APIStatusError, APITimeoutError
from schemas.jd import LLMJDResult
from schemas.resume import ResumeLLMResult
from schemas.scoring import LLMJobMatchResult
from schemas.talent import LLMTalentDiscoveryResult
from schemas.translation import LLMBatchTranslationResult


class NestedResult(BaseModel):
    note: str | None = None


class ExampleResult(BaseModel):
    items: list[NestedResult] = Field(default_factory=list)


class LLMClientStructuredOutputsTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def completion(content: str):
        return SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=content),
            )],
            usage=SimpleNamespace(
                completion_tokens=1,
                prompt_tokens=2,
                total_tokens=3,
            ),
        )

    def make_client(self, create_result=None, side_effect=None) -> LLMClient:
        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.client = Mock()
        client._provider_semaphore = asyncio.Semaphore(5)
        client.client.chat.completions.create = AsyncMock(
            return_value=create_result,
            side_effect=side_effect,
        )
        return client

    def assert_strict_schema(self, node: object) -> None:
        if isinstance(node, dict):
            self.assertNotIn("default", node)
            properties = node.get("properties")
            if isinstance(properties, dict):
                self.assertEqual(node.get("required"), list(properties))
                self.assertIs(node.get("additionalProperties"), False)
            for value in node.values():
                self.assert_strict_schema(value)
        elif isinstance(node, list):
            for value in node:
                self.assert_strict_schema(value)

    def test_all_structured_response_models_have_strict_schemas(self) -> None:
        response_models = (
            LLMJDResult,
            ResumeLLMResult,
            LLMJobMatchResult,
            LLMTalentDiscoveryResult,
            LLMBatchTranslationResult,
        )

        for response_model in response_models:
            with self.subTest(response_model=response_model.__name__):
                schema = LLMClient._build_strict_json_schema(response_model)
                self.assertEqual(schema.get("type"), "object")
                self.assert_strict_schema(schema)

    async def test_generate_structured_uses_json_object(self) -> None:
        client = self.make_client(self.completion('{"items":[{"note":null}]}'))

        result = await client.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=ExampleResult,
        )

        self.assertEqual(result, ExampleResult(items=[NestedResult(note=None)]))
        response_format = (
            client.client.chat.completions.create.await_args.kwargs[
                "response_format"
            ]
        )
        self.assertEqual(response_format, {"type": "json_object"})

    async def test_provider_concurrency_never_exceeds_five(self) -> None:
        active = 0
        maximum = 0

        async def fake_create(**_kwargs):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            try:
                await asyncio.sleep(0.01)
                return self.completion('{"items":[]}')
            finally:
                active -= 1

        client = self.make_client()
        client._provider_semaphore = asyncio.Semaphore(5)
        client.client.chat.completions.create.side_effect = fake_create

        await asyncio.gather(*[
            client.generate_structured(
                system_prompt="system",
                user_prompt=str(index),
                response_model=ExampleResult,
            )
            for index in range(12)
        ])

        self.assertEqual(maximum, 5)

    async def test_cancellation_is_not_wrapped(self) -> None:
        client = self.make_client(side_effect=asyncio.CancelledError())

        with self.assertRaises(asyncio.CancelledError):
            await client.generate_structured(
                system_prompt="system",
                user_prompt="user",
                response_model=ExampleResult,
            )

    async def test_provider_errors_keep_existing_mapping(self) -> None:
        request = httpx.Request("POST", "https://example.test/chat/completions")
        response = httpx.Response(429, request=request)
        errors = (
            APITimeoutError(request),
            APIConnectionError(request=request),
            APIStatusError("rate limited", response=response, body=None),
        )

        for error in errors:
            with self.subTest(error=type(error).__name__):
                client = self.make_client(side_effect=error)
                with self.assertRaises(LLMRequestError):
                    await client.generate_structured(
                        system_prompt="system",
                        user_prompt="user",
                        response_model=ExampleResult,
                    )

    async def test_invalid_json_and_schema_are_rejected(self) -> None:
        for content in ("not-json", '{"items":"not-a-list"}'):
            with self.subTest(content=content):
                client = self.make_client(self.completion(content))
                with self.assertRaises(LLMResponseError):
                    await client.generate_structured(
                        system_prompt="system",
                        user_prompt="user",
                        response_model=ExampleResult,
                    )

    async def test_shared_client_is_reused_and_closed(self) -> None:
        await llm_client_module.close_llm_client()
        fake_client = AsyncMock()
        with patch.object(llm_client_module, "LLMClient", return_value=fake_client) as client_class:
            first = llm_client_module.get_llm_client()
            second = llm_client_module.get_llm_client()
            self.assertIs(first, second)
            client_class.assert_called_once_with()
            await llm_client_module.close_llm_client()

        fake_client.close.assert_awaited_once_with()
        self.assertIsNone(llm_client_module._shared_llm_client)

    def test_provider_semaphore_is_process_shared_and_configurable(self) -> None:
        environment = {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://example.test",
            "LLM_MODEL": "test-model",
            "LLM_TIMEOUT": "12",
            "LLM_MAX_CONCURRENCY": "5",
        }
        with (
            patch.dict("os.environ", environment),
            patch.object(llm_client_module, "AsyncOpenAI"),
            patch.object(llm_client_module, "_provider_semaphore", None),
            patch.object(llm_client_module, "_provider_semaphore_limit", None),
        ):
            first = LLMClient()
            second = LLMClient()

        self.assertIs(first._provider_semaphore, second._provider_semaphore)
        self.assertEqual(first.max_concurrency, 5)

    def test_invalid_provider_concurrency_is_rejected(self) -> None:
        environment = {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://example.test",
            "LLM_MODEL": "test-model",
            "LLM_MAX_CONCURRENCY": "0",
        }
        with patch.dict("os.environ", environment):
            with self.assertRaises(LLMConfigError):
                LLMClient()


if __name__ == "__main__":
    unittest.main()
