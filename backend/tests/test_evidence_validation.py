import os
import unittest
from unittest.mock import Mock, patch

from schemas.evidence import EvidenceIssueReason, EvidenceVerificationStatus
from schemas.jd import JDInfo, JDRequirement
from schemas.language import AnalysisLanguage
from schemas.resume import Candidate, Project
from schemas.scoring import (
    LLMJobMatchResult,
    LLMMatchEvidence,
    LLMRequirementMatch,
    MatchConfidence,
    MatchStatus,
)
from schemas.talent import (
    LLMTalentAbility,
    LLMTalentDiscoveryResult,
    LLMTalentEvidence,
    LLMSpecifiedTraitResult,
)
from services import scoring_service, talent_service
from services.evidence_validation import verify_candidate_evidence


class EvidenceValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = Candidate(
            id="candidate_evidence_test",
            projects=[
                Project(
                    name="採用管理",
                    description="Pythonで採用管理APIを開発した。",
                ),
                Project(
                    name="社内ツール",
                    description="社内向けの集計画面を実装した。",
                ),
            ],
            skills=["Python"],
            raw_text="プロジェクトではPythonで採用管理APIを開発した。",
        )

    def test_distinguishes_raw_text_candidate_and_locator_mismatch(self) -> None:
        raw_match = verify_candidate_evidence(
            candidate=self.candidate,
            text="Pythonで採用管理APIを開発した。",
            source_type="projects",
            source_index=0,
            location="test.raw",
        )
        self.assertEqual(raw_match.verification_status, EvidenceVerificationStatus.RAW_TEXT_EXACT)
        self.assertTrue(raw_match.locator_verified)
        self.assertIsNone(raw_match.issue)

        candidate_only = verify_candidate_evidence(
            candidate=self.candidate,
            text="社内向けの集計画面を実装した。",
            source_type="projects",
            source_index=1,
            location="test.candidate",
        )
        self.assertEqual(candidate_only.verification_status, EvidenceVerificationStatus.CANDIDATE_EXACT)
        self.assertTrue(candidate_only.locator_verified)

        wrong_locator = verify_candidate_evidence(
            candidate=self.candidate,
            text="Pythonで採用管理APIを開発した。",
            source_type="projects",
            source_index=1,
            location="test.locator",
        )
        self.assertEqual(wrong_locator.verification_status, EvidenceVerificationStatus.RAW_TEXT_EXACT)
        self.assertFalse(wrong_locator.locator_verified)
        self.assertEqual(wrong_locator.issue.reason, EvidenceIssueReason.LOCATOR_MISMATCH)
        self.assertEqual(wrong_locator.source_type, "raw_text")

    def test_unverified_scoring_evidence_is_removed_and_confidence_reduced(self) -> None:
        jd = JDInfo(
            id="job_evidence_test",
            job_title="Python Engineer",
            raw_text="Python required",
            requirements=[JDRequirement(id="req_python", name="Python", weight=1)],
        )
        llm_result = LLMJobMatchResult(
            requirement_matches=[
                LLMRequirementMatch(
                    requirement_id="req_python",
                    status=MatchStatus.MATCHED,
                    score=95,
                    confidence=MatchConfidence.HIGH,
                    reason="Strong match",
                    evidence=[LLMMatchEvidence(
                        text="Led a global team of 100 engineers",
                        source_type="projects",
                        source_index=0,
                    )],
                )
            ],
            overall_confidence=MatchConfidence.HIGH,
            summary="Strong match",
        )
        client = Mock()
        client.generate_structured.return_value = llm_result

        with patch.dict(os.environ, {"SCORING_USE_MOCK": "false"}), patch.object(
            scoring_service,
            "LLMClient",
            return_value=client,
        ):
            result = scoring_service.evaluate_job_match(
                jd,
                self.candidate,
                AnalysisLanguage.EN_US,
            )

        requirement = result.requirement_results[0]
        self.assertEqual(requirement.evidence, [])
        self.assertEqual(requirement.confidence, MatchConfidence.LOW)
        self.assertEqual(result.confidence, MatchConfidence.LOW)
        self.assertTrue(requirement.needs_raw_review)
        self.assertTrue(requirement.evidence_validation_issues)
        self.assertTrue(result.warnings)
        self.assertNotEqual(result.summary, "Strong match")

    def test_unsupported_talent_ability_is_not_returned(self) -> None:
        llm_result = LLMTalentDiscoveryResult(
            mode="auto",
            attention_level="high",
            summary="High potential",
            abilities=[LLMTalentAbility(
                ability_name="Leadership",
                level="high",
                reason="Large-team leadership",
                evidence=[LLMTalentEvidence(
                    text="Led a global team of 100 engineers",
                    source_type="projects",
                    source_index=0,
                )],
            )],
        )
        with patch.dict(os.environ, {"TALENT_USE_MOCK": "false"}), patch.object(
            talent_service,
            "LLMClient",
        ) as client_class:
            client_class.return_value.generate_structured.return_value = llm_result
            result = talent_service.discover_talent(
                self.candidate,
                AnalysisLanguage.EN_US,
            )

        self.assertEqual(result.abilities, [])
        self.assertEqual(result.attention_level, "high")
        self.assertTrue(result.evidence_validation_issues)
        self.assertTrue(result.warnings)
        self.assertNotEqual(result.summary, "High potential")

    def test_unsupported_specified_trait_keeps_business_level(self) -> None:
        llm_result = LLMTalentDiscoveryResult(
            mode="specified",
            specified_fit_level="high",
            summary="Strong fit",
            specified_traits=[LLMSpecifiedTraitResult(
                trait="Integrity",
                fit_level="high",
                reason="Strong integrity",
                evidence=[LLMTalentEvidence(
                    text="Always reported every mistake immediately",
                    source_type="projects",
                    source_index=0,
                )],
            )],
        )
        with patch.dict(os.environ, {"TALENT_USE_MOCK": "false"}), patch.object(
            talent_service,
            "LLMClient",
        ) as client_class:
            client_class.return_value.generate_structured.return_value = llm_result
            result = talent_service.discover_talent(
                self.candidate,
                AnalysisLanguage.EN_US,
                mode="specified",
                desired_traits=["Integrity"],
            )

        trait = result.specified_traits[0]
        self.assertEqual(trait.evidence, [])
        self.assertEqual(trait.fit_level, "high")
        self.assertEqual(result.specified_fit_level, "high")
        self.assertTrue(trait.missing_information)
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()
