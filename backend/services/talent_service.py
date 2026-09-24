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

import hashlib
import os


def _is_talent_mock_enabled() -> bool:
    return os.getenv("TALENT_USE_MOCK", "false").strip().lower() in {"1", "true", "yes", "on"}


_MOCK_PROFILES = (
    ("high", "项目经历呈现了从主动学习到独立交付的连续过程，值得优先深入了解。", (
        ("学习落地能力", "high", "能将新知识转化为可交付的项目成果。", ("自主学习新技术并用于实际项目", "完成从方案到交付的完整实践")),
        ("独立解决问题", "high", "经历体现了独立定位问题和推进方案的能力。", ("独立处理项目中的关键问题", "持续推进项目直至上线")),
        ("跨领域迁移能力", "medium_high", "有跨技术或业务场景应用既有经验的迹象。", ("将已有技术经验迁移到新业务场景",)),
    )),
    ("medium_high", "具备持续投入和沟通协调的迹象，适合进一步核实协作成果。", (
        ("自驱力", "medium_high", "经历中有主动推进工作的描述。", ("主动承担阶段性目标并跟进结果",)),
        ("沟通协调", "medium_high", "能够在跨角色合作中推动信息对齐。", ("与不同岗位同事协作完成交付", "协调需求与实施节奏")),
        ("持续投入", "medium", "有持续参与同一方向工作的记录。", ("持续参与项目迭代与问题处理",)),
    )),
    ("medium", "执行和可靠性方面有可读线索，但尚需结合具体成果判断影响范围。", (
        ("可靠性意识", "medium", "经历强调按要求完成工作和核查结果。", ("按流程完成交付并检查结果",)),
        ("组织协调", "medium", "有协助安排任务和跟进进度的迹象。", ("协助团队安排任务与跟踪进度",)),
    )),
    ("medium_low", "当前资料中的能力描述较笼统，建议先核实具体负责范围。", (
        ("复杂问题处理", "medium_low", "提到参与复杂任务，但缺少个人决策过程。", ("参与处理项目中的复杂任务",)),
        ("新人带教", "medium_low", "有协助新人工作的线索，尚不清楚实际带教效果。", ("协助新人熟悉工作流程",)),
    )),
    ("low", "资料主要呈现基础岗位职责，额外能力证据有限。", (
        ("可靠性意识", "medium_low", "有完成日常工作的记录，独立负责范围仍需确认。", ("按要求完成日常岗位工作",)),
        ("沟通协调", "low", "可见协作经历较少，暂无法判断复杂沟通能力。", ("参与团队日常信息沟通",)),
    )),
)


def _mock_candidate_evidence(candidate: Candidate) -> LLMTalentEvidence | None:
    """从候选人已有内容选一条事实，不做关键词推理。"""
    for source_type, items in (
        ("projects", candidate.projects),
        ("work_experience", candidate.work_experience),
        ("candidate_evidence", candidate.candidate_evidence),
    ):
        if items:
            item = items[0]
            value = (item.description or getattr(item, "name", None)
                     or getattr(item, "position", None) or getattr(item, "title", None))
            if value:
                return LLMTalentEvidence(text=value[:180], source_type=source_type, source_index=0)
    if candidate.skills:
        return LLMTalentEvidence(text="、".join(candidate.skills[:4]), source_type="skills")
    return None


def _build_mock_llm_talent_result(
    candidate: Candidate, mode: TalentMode, desired_traits: list[str],
) -> LLMTalentDiscoveryResult:
    """稳定选择模拟画像并构造正式 LLM DTO。"""
    key = candidate.id or (candidate.basic_info.name if candidate.basic_info else None)
    key = key or (candidate.extraction_metadata.source_file if candidate.extraction_metadata else None) or "candidate"
    profile_index = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "big") % len(_MOCK_PROFILES)
    level, summary, ability_data = _MOCK_PROFILES[profile_index]
    candidate_fact = _mock_candidate_evidence(candidate)
    abilities = []
    for name, ability_level, reason, examples in ability_data:
        evidence = [LLMTalentEvidence(text=text, source_type="mock_profile") for text in examples]
        if candidate_fact:
            evidence.insert(0, candidate_fact.model_copy(deep=True))
        abilities.append(LLMTalentAbility(
            ability_name=name, level=ability_level, reason=reason, evidence=evidence,
        ))

    specified_traits = []
    if mode == "specified":
        for trait in dict.fromkeys(desired_traits):
            has_evidence = candidate_fact is not None and profile_index < 3
            specified_traits.append(LLMSpecifiedTraitResult(
                trait=trait,
                fit_level=level,
                reason=(f"简历中有与「{trait}」相关的事实线索，建议面试核实具体贡献。"
                        if has_evidence else f"当前资料对「{trait}」的直接支持不足，需进一步确认。"),
                evidence=[candidate_fact.model_copy(deep=True)] if has_evidence else [],
                missing_information=[] if has_evidence else [f"请核实「{trait}」的具体行为和结果"],
            ))

    return LLMTalentDiscoveryResult(
        mode=mode,
        attention_level=level if mode == "auto" else None,
        specified_fit_level=level if mode == "specified" else None,
        summary=summary,
        abilities=abilities,
        specified_traits=specified_traits,
    )


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

    if _is_talent_mock_enabled():
        llm_result = _build_mock_llm_talent_result(candidate, mode, traits)
    else:
        user_prompt = build_talent_user_prompt(
            candidate=candidate,
            mode=mode,
            desired_traits=traits,
        )
        llm_client = LLMClient()
        llm_result = llm_client.generate_structured(
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
