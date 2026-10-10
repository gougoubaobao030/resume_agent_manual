import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from pydantic import BaseModel, Field

from clients.llm_client import LLMClient
from schemas.jd import LLMJDResult
from schemas.resume import ResumeLLMResult
from schemas.scoring import LLMJobMatchResult
from schemas.talent import LLMTalentDiscoveryResult
from schemas.translation import LLMBatchTranslationResult


class NestedResult(BaseModel):
    note: str | None = None


class ExampleResult(BaseModel):
    items: list[NestedResult] = Field(default_factory=list)


class LLMClientStructuredOutputsTest(unittest.TestCase):
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

    def test_generate_structured_uses_json_object(self) -> None:
        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.client = Mock()
        client.client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content='{"items":[{"note":null}]}'),
                )
            ],
            usage=SimpleNamespace(
                completion_tokens=1,
                prompt_tokens=2,
                total_tokens=3,
            ),
        )

        result = client.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=ExampleResult,
        )

        self.assertEqual(result, ExampleResult(items=[NestedResult(note=None)]))
        response_format = (
            client.client.chat.completions.create.call_args.kwargs[
                "response_format"
            ]
        )
        self.assertEqual(response_format, {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
