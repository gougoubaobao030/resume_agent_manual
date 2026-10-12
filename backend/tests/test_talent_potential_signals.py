import os
import unittest
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from schemas.language import AnalysisLanguage
from schemas.resume import Candidate, Project
from schemas.talent import (
    POTENTIAL_DIMENSION_IDS,
    LLMTalentAbility,
    LLMTalentDiscoveryResult,
    LLMTalentEvidence,
    TalentDiscoveryResult,
)
from services import talent_service


def _ability(
    dimension_id: str,
    *,
    level: str = "medium",
    evidence: list[LLMTalentEvidence] | None = None,
) -> LLMTalentAbility:
    return LLMTalentAbility(
        ability_name=dimension_id,
        level=level,
        reason=f"Reason for {dimension_id}",
        evidence=evidence or [],
        missing_information=[] if evidence else [f"Missing facts for {dimension_id}"],
    )


def _auto_result(
    abilities: list[LLMTalentAbility],
    *,
    attention_level: str = "medium_high",
) -> LLMTalentDiscoveryResult:
    return LLMTalentDiscoveryResult(
        mode="auto",
        attention_level=attention_level,
        summary="Potential signal summary",
        abilities=abilities,
    )


class PotentialSignalSchemaTest(unittest.TestCase):
    def test_auto_requires_exactly_the_seven_dimensions(self) -> None:
        abilities = [_ability(dimension_id) for dimension_id in POTENTIAL_DIMENSION_IDS]
        result = _auto_result(abilities)
        self.assertEqual(
            [ability.ability_name for ability in result.abilities],
            list(POTENTIAL_DIMENSION_IDS),
        )

        invalid_sets = [
            abilities[:-1],
            [*abilities[:-1], _ability(POTENTIAL_DIMENSION_IDS[0])],
            [*abilities, _ability("unknown_dimension")],
        ]
        for invalid in invalid_sets:
            with self.subTest(dimensions=[item.ability_name for item in invalid]):
                with self.assertRaises(ValidationError):
                    _auto_result(invalid)

    def test_old_auto_json_remains_readable(self) -> None:
        result = TalentDiscoveryResult.model_validate({
            "candidate_id": "legacy_candidate",
            "analysis_language": "zh-CN",
            "mode": "auto",
            "attention_level": "medium",
            "summary": "旧版自由能力发现结果",
            "abilities": [{
                "ability_name": "旧版自由能力名称",
                "level": "medium",
                "reason": "旧版理由",
                "evidence": [],
                "evidence_validation_issues": [],
            }],
        })

        self.assertEqual(result.abilities[0].ability_name, "旧版自由能力名称")
        self.assertFalse(hasattr(result.abilities[0], "evidence_status"))
        self.assertFalse(hasattr(result.abilities[0], "missing_information"))


class PotentialSignalServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.candidate = Candidate(
            id="potential_signal_candidate",
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
            raw_text="プロジェクトではPythonで採用管理APIを開発した。",
        )

    async def _discover(self, llm_result: LLMTalentDiscoveryResult):
        client = AsyncMock()
        client.generate_structured.return_value = llm_result
        with patch.dict(os.environ, {"TALENT_USE_MOCK": "false"}), patch.object(
            talent_service,
            "get_llm_client",
            return_value=client,
        ):
            return await talent_service.discover_talent(
                self.candidate,
                AnalysisLanguage.EN_US,
            )

    async def test_evidence_statuses_keep_every_dimension(self) -> None:
        abilities = [_ability(dimension_id) for dimension_id in POTENTIAL_DIMENSION_IDS]
        abilities[0] = _ability(
            POTENTIAL_DIMENSION_IDS[0],
            level="high",
            evidence=[LLMTalentEvidence(
                text="Pythonで採用管理APIを開発した。",
                source_type="projects",
                source_index=0,
            )],
        )
        abilities[1] = _ability(
            POTENTIAL_DIMENSION_IDS[1],
            level="medium_high",
            evidence=[LLMTalentEvidence(
                text="Pythonで採用管理APIを開発した。",
                source_type="projects",
                source_index=1,
            )],
        )
        abilities[2] = _ability(
            POTENTIAL_DIMENSION_IDS[2],
            level="medium_high",
            evidence=[LLMTalentEvidence(
                text="Led a global team of 100 engineers",
                source_type="projects",
                source_index=0,
            )],
        )

        result = await self._discover(_auto_result(abilities))

        self.assertEqual(len(result.abilities), 7)
        self.assertEqual(result.abilities[0].evidence_status, "verified")
        self.assertEqual(result.abilities[1].evidence_status, "needs_review")
        self.assertTrue(result.abilities[1].evidence)
        self.assertEqual(result.abilities[2].evidence_status, "needs_review")
        self.assertEqual(result.abilities[2].evidence, [])
        self.assertEqual(result.abilities[3].evidence_status, "insufficient_evidence")
        self.assertEqual(result.abilities[3].level, "low")

    async def test_all_insufficient_dimensions_normalize_overall_to_low(self) -> None:
        abilities = [
            _ability(dimension_id, level="high")
            for dimension_id in reversed(POTENTIAL_DIMENSION_IDS)
        ]

        result = await self._discover(
            _auto_result(abilities, attention_level="high")
        )

        self.assertEqual(result.attention_level, "low")
        self.assertEqual(len(result.abilities), 7)
        self.assertEqual(
            [ability.ability_name for ability in result.abilities],
            list(POTENTIAL_DIMENSION_IDS),
        )
        self.assertTrue(all(
            ability.evidence_status == "insufficient_evidence"
            and ability.level == "low"
            for ability in result.abilities
        ))


if __name__ == "__main__":
    unittest.main()
