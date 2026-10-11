import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api import jd as jd_api
from api.auth import get_current_user
from app.main import app
from clients.llm_client import LLMConfigError, LLMRequestError, LLMResponseError


class AsyncLLMApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=None)
        self.addCleanup(app.dependency_overrides.clear)

    def test_jd_async_errors_keep_http_mapping(self) -> None:
        cases = (
            (LLMConfigError("bad config"), 500),
            (LLMRequestError("provider unavailable"), 503),
            (LLMResponseError("invalid response"), 502),
        )

        with TestClient(app) as client:
            for error, expected_status in cases:
                with self.subTest(error=type(error).__name__), patch.object(
                    jd_api,
                    "parse_jd",
                    new=AsyncMock(side_effect=error),
                ):
                    response = client.post(
                        "/api/jd/parse",
                        json={"raw_text": "Python engineer"},
                    )

                self.assertEqual(response.status_code, expected_status, response.text)


if __name__ == "__main__":
    unittest.main()
