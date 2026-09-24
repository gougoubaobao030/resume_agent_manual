import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from schemas.resume import BasicInfo, Candidate, Project
from schemas.talent import LLMTalentDiscoveryResult
from services import talent_service


class TalentMockTest(unittest.TestCase):
    def setUp(self):
        self.candidate = Candidate(
            id="candidate_mock_test",
            basic_info=BasicInfo(name="测试候选人"),
            projects=[Project(name="招聘系统", description="完成后端接口与前端联调")],
        )

    def test_api_auto_and_specified_skip_llm(self):
        with patch.dict(os.environ, {"TALENT_USE_MOCK": "true"}), patch.object(
            talent_service, "LLMClient", side_effect=AssertionError("LLM must not be initialized")
        ), TestClient(app) as client:
            candidate = self.candidate.model_dump()
            auto = client.post("/api/talent/discover", json={
                "candidate": candidate, "mode": "auto", "desired_traits": [],
            })
            self.assertEqual(auto.status_code, 200, auto.text)
            auto_data = auto.json()
            self.assertEqual(auto_data["mode"], "auto")
            self.assertIsNotNone(auto_data["attention_level"])
            self.assertIsNone(auto_data["specified_fit_level"])
            self.assertEqual(auto_data["specified_traits"], [])
            self.assertTrue(auto_data["summary"])
            self.assertTrue(auto_data["abilities"])
            self.assertTrue(auto_data["abilities"][0]["reason"])
            self.assertTrue(auto_data["abilities"][0]["evidence"])
            self.assertIn("warnings", auto_data)

            traits = ["认真", "负责", "学习快"]
            specified = client.post("/api/talent/discover", json={
                "candidate": candidate, "mode": "specified", "desired_traits": traits,
            })
            self.assertEqual(specified.status_code, 200, specified.text)
            data = specified.json()
            self.assertEqual(data["mode"], "specified")
            self.assertIsNone(data["attention_level"])
            self.assertIsNotNone(data["specified_fit_level"])
            self.assertEqual([item["trait"] for item in data["specified_traits"]], traits)
            self.assertTrue(data["abilities"])
            self.assertTrue(data["specified_traits"][0]["reason"])
            self.assertIn("missing_information", data["specified_traits"][0])
            self.assertIn("warnings", data)

    def test_stable_different_profiles_and_real_branch(self):
        with patch.dict(os.environ, {"TALENT_USE_MOCK": "true"}):
            first = talent_service.discover_talent(self.candidate)
            again = talent_service.discover_talent(self.candidate)
            self.assertEqual(first, again)
            profiles = {
                talent_service.discover_talent(Candidate(id=f"candidate_{index}")).attention_level
                for index in range(20)
            }
            self.assertGreaterEqual(len(profiles), 4)

        expected = LLMTalentDiscoveryResult(
            mode="auto", attention_level="medium", summary="真实分支测试", abilities=[],
        )
        with patch.dict(os.environ, {"TALENT_USE_MOCK": "false"}), patch.object(
            talent_service, "LLMClient"
        ) as client_class:
            client_class.return_value.generate_structured.return_value = expected
            result = talent_service.discover_talent(self.candidate)
            client_class.assert_called_once_with()
            client_class.return_value.generate_structured.assert_called_once()
            self.assertEqual(result.summary, "真实分支测试")


if __name__ == "__main__":
    unittest.main()
