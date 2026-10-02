import os
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from api.auth import get_current_user
from clients.llm_client import LLMResponseError
from schemas.translation import (
    BatchTranslationRequest,
    LLMBatchTranslationResult,
    LLMTranslationItem,
)
from services.translation_service import translate_batch


class TranslationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=None)
        self.addCleanup(app.dependency_overrides.clear)
        self.request = BatchTranslationRequest.model_validate({
            "target_language": "en-US",
            "items": [
                {"item_id": "summary", "text_type": "analysis", "text": "总体匹配良好"},
                {"item_id": "evidence-1", "text_type": "evidence", "text": "採用管理APIを開発した。"},
            ],
        })

    def test_mock_api_preserves_item_mapping(self) -> None:
        with patch.dict(os.environ, {"TRANSLATION_USE_MOCK": "true"}), TestClient(app) as client:
            response = client.post(
                "/api/translations/batch",
                json=self.request.model_dump(mode="json"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["target_language"], "en-US")
        self.assertEqual(
            [item["item_id"] for item in data["items"]],
            ["summary", "evidence-1"],
        )
        self.assertTrue(all(item["status"] == "success" for item in data["items"]))

    def test_service_restores_request_order_and_marks_missing_item_failed(self) -> None:
        client = Mock()
        client.generate_structured.return_value = LLMBatchTranslationResult(items=[
            LLMTranslationItem(item_id="evidence-1", translated_text="Developed a recruiting API."),
        ])

        result = translate_batch(self.request, llm_client=client)

        self.assertEqual([item.item_id for item in result.items], ["summary", "evidence-1"])
        self.assertEqual(result.items[0].status, "failed")
        self.assertEqual(result.items[1].status, "success")
        self.assertTrue(result.warnings)

    def test_unknown_item_id_is_rejected(self) -> None:
        client = Mock()
        client.generate_structured.return_value = LLMBatchTranslationResult(items=[
            LLMTranslationItem(item_id="unknown", translated_text="Unknown"),
        ])

        with self.assertRaises(LLMResponseError):
            translate_batch(self.request, llm_client=client)


if __name__ == "__main__":
    unittest.main()
