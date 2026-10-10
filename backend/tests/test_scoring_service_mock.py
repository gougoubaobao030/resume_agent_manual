import os
import unittest
from unittest.mock import Mock, patch

from schemas.jd import JDInfo, JDRequirement
from schemas.language import AnalysisLanguage
from schemas.resume import BasicInfo, Candidate, ExtractionMetadata
from schemas.scoring import (
    JobMatchResult,
    LLMJobMatchResult,
    LLMMatchEvidence,
    LLMRequirementMatch,
    MatchConfidence,
    MatchStatus,
)
from services import scoring_service


def _build_test_jd() -> JDInfo:
    return JDInfo(
        id="job_mock_test",
        job_title="测试岗位",
        raw_text="用于岗位评分 Mock 自动测试的岗位描述",
        requirements=[
            JDRequirement(
                id="req_python",
                name="Python",
                weight=3,
                must_have=True,
            ),
            JDRequirement(
                id="req_fastapi",
                name="FastAPI",
                weight=2,
            ),
            JDRequirement(
                id="req_llm",
                name="LLM应用开发",
                weight=1,
            ),
        ],
    )


def _build_test_candidate() -> Candidate:
    return Candidate(
        id="candidate_any_input",
        basic_info=BasicInfo(name="任意候选人"),
        skills=["Python", "FastAPI"],
        extraction_metadata=ExtractionMetadata(
            source_file="任意简历文件.pdf",
        ),
    )


class ScoringMockTest(unittest.TestCase):
    def test_mock_skips_prompt_and_llm_and_keeps_all_validation(self) -> None:
        jd = _build_test_jd()
        candidate = _build_test_candidate()

        with (
            patch.dict(os.environ, {"SCORING_USE_MOCK": "true"}),
            patch.object(
                scoring_service,
                "_build_job_match_prompt",
                side_effect=AssertionError("Mock 不应构造真实评分 Prompt"),
            ),
            patch.object(
                scoring_service,
                "LLMClient",
                side_effect=AssertionError("Mock 不应初始化 LLM"),
            ),
            patch.object(
                scoring_service,
                "_validate_requirement_coverage",
                wraps=scoring_service._validate_requirement_coverage,
            ) as coverage_mock,
            patch.object(
                scoring_service,
                "_validate_job_match_result_consistency",
                wraps=scoring_service._validate_job_match_result_consistency,
            ) as consistency_mock,
        ):
            result = scoring_service.evaluate_job_match(jd, candidate, AnalysisLanguage.ZH_CN)

        coverage_mock.assert_called_once()
        consistency_mock.assert_called_once()
        validated_result = JobMatchResult.model_validate(result.model_dump())
        self.assertEqual(
            [item.requirement_id for item in validated_result.requirement_results],
            [item.id for item in jd.requirements],
        )
        self.assertTrue(
            all(item.evidence for item in validated_result.requirement_results)
        )

    def test_mock_is_stable_for_same_candidate_and_jd(self) -> None:
        jd = _build_test_jd()
        candidate = _build_test_candidate()

        with patch.dict(os.environ, {"SCORING_USE_MOCK": "true"}):
            first = scoring_service.evaluate_job_match(jd, candidate, AnalysisLanguage.JA_JP)
            second = scoring_service.evaluate_job_match(jd, candidate, AnalysisLanguage.JA_JP)

        self.assertEqual(first, second)

    def test_real_mode_uses_existing_prompt_and_llm_path(self) -> None:
        jd = _build_test_jd()
        candidate = _build_test_candidate()
        llm_result = LLMJobMatchResult(
            requirement_matches=[
                LLMRequirementMatch(
                    requirement_id=requirement.id,
                    status=MatchStatus.MATCHED,
                    score=80,
                    confidence=MatchConfidence.HIGH,
                    reason="测试替身返回",
                    evidence=[
                        LLMMatchEvidence(
                            text="测试替身证据",
                        )
                    ],
                )
                for requirement in jd.requirements
            ],
            overall_confidence=MatchConfidence.HIGH,
            summary="真实分支测试替身结果",
        )
        client = Mock()
        client.generate_structured.return_value = llm_result

        with (
            patch.dict(os.environ, {"SCORING_USE_MOCK": "false"}),
            patch.object(
                scoring_service,
                "LLMClient",
                return_value=client,
            ) as client_class_mock,
            patch.object(
                scoring_service,
                "_build_job_match_prompt",
                wraps=scoring_service._build_job_match_prompt,
            ) as prompt_mock,
        ):
            result = scoring_service.evaluate_job_match(jd, candidate, AnalysisLanguage.EN_US)

        client_class_mock.assert_called_once_with()
        prompt_mock.assert_called_once_with(
            jd=jd,
            candidate=candidate,
            analysis_language=AnalysisLanguage.EN_US,
        )
        client.generate_structured.assert_called_once()
        self.assertEqual(result.candidate_id, candidate.id)
        self.assertEqual(result.analysis_language, AnalysisLanguage.EN_US)

    def test_scoring_prompt_payload_excludes_jd_raw_text(self) -> None:
        jd = _build_test_jd()
        candidate = _build_test_candidate()

        with patch.object(
            scoring_service,
            "build_job_match_user_prompt",
            return_value="prompt",
        ) as builder_mock:
            prompt = scoring_service._build_job_match_prompt(
                jd=jd,
                candidate=candidate,
                analysis_language=AnalysisLanguage.ZH_CN,
            )

        self.assertEqual(prompt, "prompt")
        jd_data = builder_mock.call_args.kwargs["jd_data"]
        self.assertEqual(set(jd_data), {"id", "job_title", "requirements"})
        self.assertNotIn("raw_text", jd_data)
        self.assertEqual(jd_data["job_title"], jd.job_title)
        self.assertEqual(
            [item["id"] for item in jd_data["requirements"]],
            [item.id for item in jd.requirements],
        )


if __name__ == "__main__":
    unittest.main()
