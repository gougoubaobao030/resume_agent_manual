from schemas.resume import Candidate
from schemas.talent import (
    TalentMode,
    TalentEvidence,
    TalentAbility,
    SpecifiedTraitResult,
    TalentDiscoveryResult,
    LLMTalentEvidence,
    LLMTalentAbility,
    LLMSpecifiedTraitResult,
    LLMTalentDiscoveryResult,
)

from prompts.talent_prompt import (
    TALENT_SYSTEM_PROMPT,
    build_talent_user_prompt,
)

from clients.llm_client import LLMClient


def discover_talent(
    candidate: Candidate,
    mode: TalentMode = "auto",
    desired_traits: list[str] | None = None,
) -> TalentDiscoveryResult:
    """分析候选人的人才能力与值得关注的特征。"""

    traits = desired_traits or []

    _validate_request(
        mode=mode,
        desired_traits=traits,
    )

    user_prompt = build_talent_user_prompt(
        candidate=candidate,
        mode=mode,
        desired_traits=traits,
    )

    llm_clinet = LLMClient()

    llm_result = llm_clinet.generate_structured(
        system_prompt=TALENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=LLMTalentDiscoveryResult,
    )

    if mode == "specified":
        _validate_specified_trait_coverage(
            desired_traits=traits,
            llm_result=llm_result,
        )

    abilities = [
        _build_talent_ability(ability)
        for ability in llm_result.abilities
    ]

    specified_traits = [
        _build_specified_trait_result(trait_result)
        for trait_result in llm_result.specified_traits
    ]

    warnings = _build_warnings(
        mode=mode,
        llm_result=llm_result,
    )

    return TalentDiscoveryResult(
        candidate_id=candidate.id,
        mode=mode,
        attention_level=llm_result.attention_level,
        specified_fit_level=llm_result.specified_fit_level,
        summary=llm_result.summary,
        abilities=abilities,
        specified_traits=specified_traits,
        warnings=warnings,
    )


def _validate_request(
    mode: TalentMode,
    desired_traits: list[str],
) -> None:
    """校验人才能力发现请求。"""

    if mode == "specified" and not desired_traits:
        raise ValueError(
            "specified模式必须提供desired_traits"
        )

    if mode == "auto" and desired_traits:
        raise ValueError(
            "auto模式不应提供desired_traits"
        )


def _validate_specified_trait_coverage(
    desired_traits: list[str],
    llm_result: LLMTalentDiscoveryResult,
) -> None:
    """检查LLM是否完整且唯一地分析了所有HR指定人才特征。"""

    expected_traits = set(desired_traits)

    actual_traits = [
        result.trait
        for result in llm_result.specified_traits
    ]

    actual_trait_set = set(actual_traits)

    if len(actual_traits) != len(actual_trait_set):
        raise ValueError(
            "LLM人才像分析结果包含重复trait"
        )

    missing_traits = expected_traits - actual_trait_set
    unknown_traits = actual_trait_set - expected_traits

    if missing_traits:
        raise ValueError(
            f"LLM人才像分析结果缺少trait: "
            f"{sorted(missing_traits)}"
        )

    if unknown_traits:
        raise ValueError(
            f"LLM人才像分析结果包含未指定trait: "
            f"{sorted(unknown_traits)}"
        )


def _build_talent_evidence(
    llm_evidence: LLMTalentEvidence,
) -> TalentEvidence:
    """将LLM证据DTO转换为系统内部证据模型。"""

    return TalentEvidence(
        text=llm_evidence.text,
        source_type=llm_evidence.source_type,
        source_index=llm_evidence.source_index,
    )


def _build_talent_ability(
    llm_ability: LLMTalentAbility,
) -> TalentAbility:
    """将LLM能力发现结果转换为正式业务模型。"""

    return TalentAbility(
        ability_name=llm_ability.ability_name,
        level=llm_ability.level,
        reason=llm_ability.reason,
        evidence=[
            _build_talent_evidence(evidence)
            for evidence in llm_ability.evidence
        ],
    )


def _build_specified_trait_result(
    llm_result: LLMSpecifiedTraitResult,
) -> SpecifiedTraitResult:
    """将LLM指定人才像分析结果转换为正式业务模型。"""

    return SpecifiedTraitResult(
        trait=llm_result.trait,
        fit_level=llm_result.fit_level,
        reason=llm_result.reason,
        evidence=[
            _build_talent_evidence(evidence)
            for evidence in llm_result.evidence
        ],
        missing_information=llm_result.missing_information,
    )


def _build_warnings(
    mode: TalentMode,
    llm_result: LLMTalentDiscoveryResult,
) -> list[str]:
    """根据分析结果生成系统提示。"""

    warnings: list[str] = []

    if not llm_result.abilities:
        warnings.append(
            "当前候选人资料中未发现足够明确的额外能力证据"
        )

    # 指定当中任意一条不满足就会加入warnings
    # 并附上是哪个不满足是A项还是B项，C项等等
    if mode == "specified":
        evidence_missing_traits = [
            result.trait
            for result in llm_result.specified_traits
            if not result.evidence
        ]

        if evidence_missing_traits:
            warnings.append(
                "以下指定人才特征当前资料证据不足: "
                + "、".join(evidence_missing_traits)
            )

    return warnings