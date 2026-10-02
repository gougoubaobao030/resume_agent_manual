import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.main import app
from api.auth import get_current_user
from prompts.scoring_prompt import build_job_match_user_prompt
from prompts.talent_prompt import build_talent_user_prompt
from schemas.jd import JDInfo, JDRequirement
from schemas.language import AnalysisLanguage
from schemas.resume import BasicInfo, Candidate, Project
from schemas.scoring import JobMatchRequest
from schemas.talent import TalentDiscoveryRequest
from services.scoring_service import evaluate_job_match
from services.talent_service import discover_talent
from services.jd_repository import save_jd
from services.jd_repository import delete_jd
from services.candidate_repository import save_candidate_for_job, delete_candidate


class AnalysisLanguageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.jd = JDInfo(
            id="job_language_test",
            job_title="Backend Engineer",
            raw_text="Backend Engineer with Python experience required.",
            requirements=[
                JDRequirement(
                    id="req_python",
                    name="Python experience",
                    description="Professional Python development experience",
                    weight=1,
                    must_have=True,
                )
            ],
        )
        self.candidate = Candidate(
            id="candidate_language_test",
            basic_info=BasicInfo(name="山田太郎"),
            projects=[
                Project(
                    name="採用システム",
                    description="Pythonで採用管理APIを開発した。",
                )
            ],
            raw_text="採用システムでPythonを使用し、採用管理APIを開発した。",
        )

    def test_request_schemas_require_supported_language(self) -> None:
        with self.assertRaises(ValidationError):
            JobMatchRequest.model_validate({
                "job_id": self.jd.id,
                "candidate_id": self.candidate.id,
            })

        with self.assertRaises(ValidationError):
            TalentDiscoveryRequest.model_validate({
                "candidate_id": self.candidate.id,
                "mode": "auto",
                "analysis_language": "fr-FR",
            })

    def test_prompts_state_language_and_preserve_original_evidence(self) -> None:
        scoring_prompt = build_job_match_user_prompt(
            jd_data=self.jd.model_dump(),
            candidate_data=self.candidate.model_dump(),
            analysis_language=AnalysisLanguage.EN_US,
        )
        talent_prompt = build_talent_user_prompt(
            candidate=self.candidate,
            mode="auto",
            analysis_language=AnalysisLanguage.JA_JP,
        )

        self.assertIn("English", scoring_prompt)
        self.assertIn("en-US", scoring_prompt)
        self.assertIn("evidence 不得为了符合分析语言而翻译或改写", scoring_prompt)
        self.assertIn("ja-JP", talent_prompt)
        self.assertIn("evidence.text 必须保持候选人资料中的原始语言", talent_prompt)

    def test_mock_results_echo_language_without_changing_scores(self) -> None:
        with patch.dict(os.environ, {
            "SCORING_USE_MOCK": "true",
            "TALENT_USE_MOCK": "true",
        }):
            scoring_results = {
                language: evaluate_job_match(self.jd, self.candidate, language)
                for language in AnalysisLanguage
            }
            talent_results = {
                language: discover_talent(self.candidate, language)
                for language in AnalysisLanguage
            }

        scores = {result.score for result in scoring_results.values()}
        statuses = {
            tuple(item.status for item in result.requirement_results)
            for result in scoring_results.values()
        }
        self.assertEqual(len(scores), 1)
        self.assertEqual(len(statuses), 1)

        for language, result in scoring_results.items():
            self.assertEqual(result.analysis_language, language)
            self.assertEqual(result.requirement_results[0].evidence[0].text, "Pythonで採用管理APIを開発した。")

        for language, result in talent_results.items():
            self.assertEqual(result.analysis_language, language)
            self.assertEqual(result.abilities[0].evidence[0].text, "Pythonで採用管理APIを開発した。")

    def test_scoring_api_requires_and_echoes_analysis_language(self) -> None:
        delete_candidate(self.candidate.id)
        delete_jd(self.jd.id)
        save_jd(self.jd)
        save_candidate_for_job(self.candidate, self.jd.id, None)
        payload = {
            "job_id": self.jd.id,
            "candidate_id": self.candidate.id,
        }
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=None)
        try:
            with patch.dict(os.environ, {"SCORING_USE_MOCK": "true"}), TestClient(app) as client:
                missing = client.post("/api/scoring/job-match", json=payload)
                success = client.post(
                    "/api/scoring/job-match",
                    json={**payload, "analysis_language": "ja-JP"},
                )
        finally:
            app.dependency_overrides.clear()
            delete_candidate(self.candidate.id)
            delete_jd(self.jd.id)

        self.assertEqual(missing.status_code, 422)
        self.assertEqual(success.status_code, 200, success.text)
        self.assertEqual(success.json()["analysis_language"], "ja-JP")


if __name__ == "__main__":
    unittest.main()
