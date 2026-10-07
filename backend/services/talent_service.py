from schemas.resume import Candidate
from schemas.language import AnalysisLanguage
from schemas.evidence import EvidenceValidationIssue
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
from services.evidence_validation import verify_candidate_evidence

import hashlib
import os


def _is_talent_mock_enabled() -> bool:
    return os.getenv("TALENT_USE_MOCK", "false").strip().lower() in {"1", "true", "yes", "on"}


_MOCK_PROFILE_LEVELS = (
    "high",
    "medium_high",
    "medium",
    "medium_low",
    "low",
)

_TALENT_LANGUAGE_TEXT = {
    AnalysisLanguage.ZH_CN: {
        "summary": "Mock 人才能力分析已完成；当前等级为 {level}，请结合原始资料人工复核。",
        "ability_name": "事实归纳能力",
        "ability_reason": "候选人资料中存在可供进一步核实的事实线索。",
        "specified_supported": "资料中存在与「{trait}」相关的事实线索，建议面试核实具体贡献。",
        "specified_missing": "当前资料缺少足够直接证据，暂无法确认「{trait}」。",
        "missing_information": "请核实「{trait}」的具体行为和结果",
        "no_abilities": "当前候选人资料中未发现足够明确的额外能力证据",
        "missing_traits": "以下指定人才特征当前资料证据不足: {traits}",
        "auto_evidence_warning": "部分 AI 能力证据未能通过简历核验；无有效证据的能力结论已自动移除，标记为待复核的保留结论需要人工确认。",
        "specified_evidence_warning": "部分指定人才像缺少可验证证据，相关项目已标记为证据不足，需要人工确认。",
        "unsupported_summary": "当前人才分析结论缺少可验证证据，已按证据不足处理，需要人工复核候选人原始资料。",
    },
    AnalysisLanguage.JA_JP: {
        "summary": "Mock 人材能力分析が完了しました。現在のレベルは {level} です。原資料と照合して確認してください。",
        "ability_name": "事実整理力",
        "ability_reason": "候補者資料には、さらに確認できる事実上の手がかりがあります。",
        "specified_supported": "資料には「{trait}」に関連する事実上の手がかりがあります。面接で具体的な貢献を確認してください。",
        "specified_missing": "現在の資料には十分な直接的根拠がなく、「{trait}」は現時点で確認できません。",
        "missing_information": "「{trait}」に関する具体的な行動と結果を確認してください",
        "no_abilities": "現在の候補者資料では、明確な追加能力の根拠を十分に確認できませんでした",
        "missing_traits": "次の指定人材特性は現在の資料で根拠が不足しています: {traits}",
        "auto_evidence_warning": "一部の AI 能力の根拠を履歴書で確認できませんでした。有効な根拠のない評価は自動的に除外し、要確認のまま残る評価は人による確認が必要です。",
        "specified_evidence_warning": "一部の指定人材特性には検証可能な根拠がなく、根拠不足として人による確認が必要です。",
        "unsupported_summary": "現在の人材分析結論には検証可能な根拠が不足しているため、根拠不足として扱い、候補者の原資料を人が確認する必要があります。",
    },
    AnalysisLanguage.EN_US: {
        "summary": "Mock capability analysis completed at level {level}; review it against the original candidate material.",
        "ability_name": "Fact synthesis",
        "ability_reason": "The candidate material contains factual signals that can be verified further.",
        "specified_supported": "The material contains factual signals related to “{trait}”; verify the candidate's specific contribution in an interview.",
        "specified_missing": "The current material lacks sufficient direct evidence to determine “{trait}”.",
        "missing_information": "Confirm the specific behavior and outcome related to “{trait}”",
        "no_abilities": "No sufficiently clear evidence of additional capabilities was found in the current candidate material",
        "missing_traits": "The current material has insufficient evidence for these target traits: {traits}",
        "auto_evidence_warning": "Some AI capability evidence could not be verified against the resume; findings without valid evidence were removed automatically, and retained findings marked for review need human confirmation.",
        "specified_evidence_warning": "Some specified talent traits lack verifiable evidence and were marked as insufficient evidence for human confirmation.",
        "unsupported_summary": "The current talent-analysis conclusions lack verifiable evidence and were treated as insufficiently supported; review the original candidate material.",
    },
}


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
        return LLMTalentEvidence(
            text=candidate.skills[0],
            source_type="skills",
            source_index=0,
        )
    if candidate.raw_text:
        return LLMTalentEvidence(
            text=candidate.raw_text[:180],
            source_type="raw_text",
        )
    return None


def _build_mock_llm_talent_result(
    candidate: Candidate,
    mode: TalentMode,
    desired_traits: list[str],
    analysis_language: AnalysisLanguage,
) -> LLMTalentDiscoveryResult:
    """稳定选择模拟画像并构造正式 LLM DTO。"""
    key = candidate.id or (candidate.basic_info.name if candidate.basic_info else None)
    key = key or (candidate.extraction_metadata.source_file if candidate.extraction_metadata else None) or "candidate"
    profile_index = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "big") % len(_MOCK_PROFILE_LEVELS)
    level = _MOCK_PROFILE_LEVELS[profile_index]
    messages = _TALENT_LANGUAGE_TEXT[analysis_language]
    candidate_fact = _mock_candidate_evidence(candidate)
    abilities = [
        LLMTalentAbility(
            ability_name=messages["ability_name"],
            level=level,
            reason=messages["ability_reason"],
            evidence=[candidate_fact.model_copy(deep=True)],
        )
    ] if candidate_fact else []

    specified_traits = []
    if mode == "specified":
        for trait in dict.fromkeys(desired_traits):
            has_evidence = candidate_fact is not None and profile_index < 3
            specified_traits.append(LLMSpecifiedTraitResult(
                trait=trait,
                fit_level=level,
                reason=(messages["specified_supported"].format(trait=trait)
                        if has_evidence else messages["specified_missing"].format(trait=trait)),
                evidence=[candidate_fact.model_copy(deep=True)] if has_evidence else [],
                missing_information=[] if has_evidence else [messages["missing_information"].format(trait=trait)],
            ))

    return LLMTalentDiscoveryResult(
        mode=mode,
        attention_level=level if mode == "auto" else None,
        specified_fit_level=level if mode == "specified" else None,
        summary=messages["summary"].format(level=level),
        abilities=abilities,
        specified_traits=specified_traits,
    )


def discover_talent(
    candidate: Candidate,
    analysis_language: AnalysisLanguage,
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
        llm_result = _build_mock_llm_talent_result(
            candidate,
            mode,
            traits,
            analysis_language,
        )
    else:
        user_prompt = build_talent_user_prompt(
            candidate=candidate,
            mode=mode,
            analysis_language=analysis_language,
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

    abilities: list[TalentAbility] = []
    removed_ability_count = 0
    evidence_validation_issues: list[EvidenceValidationIssue] = []
    for index, ability in enumerate(llm_result.abilities):
        built_ability = _build_talent_ability(
            ability,
            candidate,
            f"abilities[{index}]",
        )
        evidence_validation_issues.extend(built_ability.evidence_validation_issues)
        # 人才能力结论必须有可验证事实；否则不作为正式能力发现返回。
        if built_ability.evidence:
            abilities.append(built_ability)
        else:
            removed_ability_count += 1

    specified_traits: list[SpecifiedTraitResult] = []
    for index, trait_result in enumerate(llm_result.specified_traits):
        built_trait = _build_specified_trait_result(
            trait_result,
            candidate,
            f"specified_traits[{index}]",
            analysis_language,
        )
        evidence_validation_issues.extend(built_trait.evidence_validation_issues)
        specified_traits.append(built_trait)

    warnings = _build_warnings(
        mode=mode,
        abilities=abilities,
        specified_traits=specified_traits,
        evidence_issue_count=len(evidence_validation_issues),
        removed_ability_count=removed_ability_count,
        analysis_language=analysis_language,
    )

    summary = llm_result.summary
    if (
        (
            mode == "auto"
            and not abilities
            and evidence_validation_issues
        )
        or (
            mode == "specified"
            and specified_traits
            and not any(item.evidence for item in specified_traits)
        )
    ):
        summary = _TALENT_LANGUAGE_TEXT[analysis_language]["unsupported_summary"]

    return TalentDiscoveryResult(
        candidate_id=candidate.id,
        analysis_language=analysis_language,
        mode=mode,
        attention_level=llm_result.attention_level,
        specified_fit_level=llm_result.specified_fit_level,
        summary=summary,
        abilities=abilities,
        specified_traits=specified_traits,
        warnings=warnings,
        evidence_validation_issues=evidence_validation_issues,
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
    evidence_items: list[LLMTalentEvidence],
    candidate: Candidate,
    location: str,
) -> tuple[list[TalentEvidence], list[EvidenceValidationIssue]]:
    """只保留可从 Candidate 或 raw_text 精确确认的人才分析证据。"""

    verified: list[TalentEvidence] = []
    issues: list[EvidenceValidationIssue] = []
    for index, evidence in enumerate(evidence_items):
        check = verify_candidate_evidence(
            candidate=candidate,
            text=evidence.text,
            source_type=evidence.source_type,
            source_index=evidence.source_index,
            location=f"{location}.evidence[{index}]",
        )
        if check.issue:
            issues.append(check.issue)
        if not check.is_verified:
            continue
        verified.append(TalentEvidence(
            text=evidence.text,
            source_type=check.source_type,
            source_index=check.source_index,
            verification_status=check.verification_status,
            source_path=check.source_path,
            locator_verified=check.locator_verified,
        ))
    return verified, issues


def _build_talent_ability(
    llm_ability: LLMTalentAbility,
    candidate: Candidate,
    location: str,
) -> TalentAbility:
    """将LLM能力发现结果转换为正式业务模型。"""

    evidence, issues = _build_talent_evidence(
        llm_ability.evidence,
        candidate,
        location,
    )
    return TalentAbility(
        ability_name=llm_ability.ability_name,
        level=llm_ability.level,
        reason=llm_ability.reason,
        evidence=evidence,
        evidence_validation_issues=issues,
    )


def _build_specified_trait_result(
    llm_result: LLMSpecifiedTraitResult,
    candidate: Candidate,
    location: str,
    analysis_language: AnalysisLanguage,
) -> SpecifiedTraitResult:
    """将LLM指定人才像分析结果转换为正式业务模型。"""

    evidence, issues = _build_talent_evidence(
        llm_result.evidence,
        candidate,
        location,
    )
    missing_information = list(llm_result.missing_information)
    if not evidence:
        message = _TALENT_LANGUAGE_TEXT[analysis_language]["missing_information"].format(
            trait=llm_result.trait,
        )
        if message not in missing_information:
            missing_information.append(message)

    return SpecifiedTraitResult(
        trait=llm_result.trait,
        fit_level=llm_result.fit_level,
        reason=(
            llm_result.reason
            if evidence
            else _TALENT_LANGUAGE_TEXT[analysis_language]["specified_missing"].format(
                trait=llm_result.trait,
            )
        ),
        evidence=evidence,
        evidence_validation_issues=issues,
        missing_information=missing_information,
    )


def _build_warnings(
    mode: TalentMode,
    abilities: list[TalentAbility],
    specified_traits: list[SpecifiedTraitResult],
    evidence_issue_count: int,
    removed_ability_count: int,
    analysis_language: AnalysisLanguage,
) -> list[str]:
    """根据分析结果生成系统提示。"""

    warnings: list[str] = []
    messages = _TALENT_LANGUAGE_TEXT[analysis_language]

    if (
        mode == "auto"
        and not abilities
        and not evidence_issue_count
        and not removed_ability_count
    ):
        warnings.append(
            messages["no_abilities"]
        )

    # 指定当中任意一条不满足就会加入warnings
    # 并附上是哪个不满足是A项还是B项，C项等等
    if mode == "specified":
        evidence_missing_traits = [
            result.trait
            for result in specified_traits
            if not result.evidence
        ]

        if evidence_missing_traits:
            warnings.append(
                messages["missing_traits"].format(
                    traits="、".join(evidence_missing_traits),
                )
            )

    if mode == "auto" and (evidence_issue_count or removed_ability_count):
        warnings.append(messages["auto_evidence_warning"])
    elif mode == "specified" and evidence_issue_count:
        warnings.append(messages["specified_evidence_warning"])

    return warnings
