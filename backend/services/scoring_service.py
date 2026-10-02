from clients.llm_client import LLMClient
from prompts.scoring_prompt import (
    JOB_MATCH_SYSTEM_PROMPT,
    build_job_match_user_prompt,
)
from schemas.jd import JDInfo
from schemas.evidence import EvidenceValidationIssue
from schemas.language import AnalysisLanguage
from schemas.resume import Candidate
from schemas.scoring import LLMJobMatchResult

import hashlib
import logging
import os

from clients.llm_client import LLMClient
from prompts.scoring_prompt import (
    JOB_MATCH_SYSTEM_PROMPT,
    build_job_match_user_prompt,
)
from schemas.jd import JDInfo
from schemas.resume import Candidate
#from schemas.scoring import LLMJobMatchResult
from schemas.scoring import (
    JobMatchResult,
    LLMMatchEvidence,
    LLMJobMatchResult,
    LLMRequirementMatch,
    MatchEvidence,
    MatchConfidence,
    MatchStatus,
    MustHaveSummary,
    RawReviewRequest,
    RequirementMatchResult,
)
from services.evidence_validation import verify_candidate_evidence

logger = logging.getLogger("uvicorn.error")


def _is_scoring_mock_enabled() -> bool:
    """判断是否启用岗位匹配评分 Mock。"""

    return os.getenv(
        "SCORING_USE_MOCK",
        "false",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_mock_evidence(candidate: Candidate) -> LLMMatchEvidence | None:
    """从本次请求的 Candidate 中选择一条最小合法 Mock 证据。"""

    for source_type, items in (
        ("projects", candidate.projects),
        ("work_experience", candidate.work_experience),
        ("candidate_evidence", candidate.candidate_evidence),
    ):
        for index, item in enumerate(items):
            value = (
                getattr(item, "description", None)
                or getattr(item, "name", None)
                or getattr(item, "position", None)
                or getattr(item, "title", None)
            )
            if value:
                return LLMMatchEvidence(
                    text=value,
                    source_type=source_type,
                    source_index=index,
                )

    if candidate.skills:
        return LLMMatchEvidence(
            text=candidate.skills[0],
            source_type="skills",
            source_index=0,
        )

    if candidate.basic_info and candidate.basic_info.name:
        return LLMMatchEvidence(
            text=candidate.basic_info.name,
            source_type="basic_info",
        )

    if candidate.raw_text:
        return LLMMatchEvidence(
            text=candidate.raw_text[:180],
            source_type="raw_text",
        )

    return None


_SCORING_MOCK_TEXT = {
    AnalysisLanguage.ZH_CN: {
        "reason": "Mock 岗位匹配结果：{requirement_name}",
        "summary": "Mock 岗位匹配结果，用于无真实 LLM 成本的异步学习。",
    },
    AnalysisLanguage.JA_JP: {
        "reason": "Mock 求人マッチング結果：{requirement_name}",
        "summary": "実際の LLM コストを使わずに非同期処理を確認するための Mock 求人マッチング結果です。",
    },
    AnalysisLanguage.EN_US: {
        "reason": "Mock job-match result: {requirement_name}",
        "summary": "Mock job-match result for testing asynchronous behavior without real LLM cost.",
    },
}

_SCORING_EVIDENCE_TEXT = {
    AnalysisLanguage.ZH_CN: {
        "missing": "当前结论缺少可从候选人资料精确确认的证据，需要人工复核。",
        "review": "模型返回的证据未能全部通过原文校验，建议回查候选人资料。",
        "warning": "部分岗位匹配证据未能通过原文或来源定位校验，相关结论的可信度已降低。",
        "unsupported_reason": "模型给出了匹配判断，但其引用内容无法从候选人资料中精确确认，因此该结论需要人工复核。",
        "unsupported_summary": "当前岗位匹配结论缺少可验证证据，分数仅供参考，需要人工复核候选人原始资料。",
    },
    AnalysisLanguage.JA_JP: {
        "missing": "現在の結論には候補者資料から正確に確認できる根拠がなく、人による確認が必要です。",
        "review": "モデルが返した根拠の一部が原文照合を通過しなかったため、候補者資料を再確認してください。",
        "warning": "一部の求人マッチング根拠は原文または出典位置を確認できず、関連する結論の信頼度を下げました。",
        "unsupported_reason": "モデルはマッチング判定を返しましたが、引用内容を候補者資料から正確に確認できないため、人による確認が必要です。",
        "unsupported_summary": "現在の求人マッチング結論には検証可能な根拠が不足しています。スコアは参考情報として扱い、候補者の原資料を確認してください。",
    },
    AnalysisLanguage.EN_US: {
        "missing": "This conclusion lacks evidence that can be confirmed exactly in the candidate material and requires human review.",
        "review": "Some model-provided evidence did not pass source-text validation; review the candidate material.",
        "warning": "Some job-match evidence failed source-text or locator validation, so confidence in the related conclusions was reduced.",
        "unsupported_reason": "The model returned a match judgment, but its cited content could not be confirmed exactly in the candidate material, so human review is required.",
        "unsupported_summary": "The current job-match conclusions lack verifiable evidence. Treat the score as provisional and review the original candidate material.",
    },
}


def _build_mock_llm_job_match_result(
    jd: JDInfo,
    candidate: Candidate,
    analysis_language: AnalysisLanguage,
) -> LLMJobMatchResult:
    """根据实际 JD requirements 构造正式 LLM 评分结果模型。"""

    evidence = _build_mock_evidence(candidate)
    messages = _SCORING_MOCK_TEXT[analysis_language]
    requirement_matches: list[LLMRequirementMatch] = []

    for requirement in jd.requirements:
        stable_key = f"{candidate.id}|{requirement.id}".encode("utf-8")
        score = float(78 + hashlib.sha256(stable_key).digest()[0] % 13)
        status = (
            MatchStatus.MATCHED
            if score >= 84
            else MatchStatus.PARTIALLY_MATCHED
        )
        confidence = (
            MatchConfidence.HIGH
            if status == MatchStatus.MATCHED
            else MatchConfidence.MEDIUM
        )

        requirement_matches.append(
            LLMRequirementMatch(
                requirement_id=requirement.id,
                status=status,
                score=score,
                confidence=confidence,
                reason=(
                    messages["reason"].format(
                        requirement_name=requirement.name,
                    )
                ),
                evidence=[evidence.model_copy(deep=True)] if evidence else [],
                missing_information=[],
                needs_raw_review=False,
                raw_review_reason=None,
            )
        )

    return LLMJobMatchResult(
        requirement_matches=requirement_matches,
        overall_confidence=MatchConfidence.MEDIUM,
        summary=messages["summary"],
        missing_information=[],
        needs_raw_review=False,
        raw_review_requirement_ids=[],
    )


def _build_job_match_prompt(
    jd: JDInfo,
    candidate: Candidate,
    analysis_language: AnalysisLanguage,
) -> str:
    """将业务模型转换为岗位匹配Prompt输入。"""

    return build_job_match_user_prompt(
        jd_data=jd.model_dump(),
        candidate_data=candidate.model_dump(),
        analysis_language=analysis_language,
    )

# 这里学到了很重要的一点
# 继续Pydantic校验数据结构是否合法后
# 这里校验输出内容是否合法（当然不是全部内容）
# 学到就算给了requirements，模型也可能抽风
# 完全不按照要求的5条来，会多一条或者少一条或者重复，很风险
def _validate_requirement_coverage(
    jd: JDInfo,
    llm_result: LLMJobMatchResult,
) -> None:
    """检查LLM是否完整且唯一地评价了所有JD要求。"""
    
    # 提取 JD 中所有 requirement 的 id，组成一个 set 集合。
    # 用于和模型实际返回的 requirement_id 做对比，检查遗漏或多余项。
    expected_ids = {
        requirement.id
        for requirement in jd.requirements
    }

    actual_ids = [
        match.requirement_id
        for match in llm_result.requirement_matches
    ]

    actual_id_set = set(actual_ids)

    if len(actual_ids) != len(actual_id_set):
        raise ValueError(
            "LLM岗位匹配结果包含重复的requirement_id"
        )

    missing_ids = expected_ids - actual_id_set
    unknown_ids = actual_id_set - expected_ids

    if missing_ids:
        # 扔出一个错误，而不是捕获别人扔的业务错误
        raise ValueError(
            f"LLM岗位匹配结果缺少requirement: {sorted(missing_ids)}"
        )

    if unknown_ids:
        raise ValueError(
            f"LLM岗位匹配结果包含不存在的requirement: {sorted(unknown_ids)}"
        )

# 核心函数一号
# 业务层第一件事，就是把已经有的jbinfo和candidate拿去让大模型评分给个
# LLM响应总结果
def evaluate_job_match_with_llm(
    jd: JDInfo,
    candidate: Candidate,
    analysis_language: AnalysisLanguage,
) -> LLMJobMatchResult:
    """使用LLM对结构化JD和结构化候选人进行岗位匹配判断。"""

    if _is_scoring_mock_enabled():
        logger.info(
            "[Scoring Mock] candidate=%s job=%s",
            candidate.id,
            jd.id,
        )

        result = _build_mock_llm_job_match_result(
            jd=jd,
            candidate=candidate,
            analysis_language=analysis_language,
        )

        _validate_requirement_coverage(
            jd=jd,
            llm_result=result,
        )

        return result

    user_prompt = _build_job_match_prompt(
        jd=jd,
        candidate=candidate,
        analysis_language=analysis_language,
    )

    llm_client = LLMClient()

    result = llm_client.generate_structured(
        system_prompt=JOB_MATCH_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=LLMJobMatchResult,
    )

    _validate_requirement_coverage(
        jd=jd,
        llm_result=result,
    )

    return result

# 重写权重归一化, 之后用于核心函数二号：
# mapper大模型响应结果
def _normalize_requirement_weights(
    jd: JDInfo,
) -> dict[str, float]:
    """将JD requirement原始权重归一化为0~1，总和为1。"""

    if not jd.requirements:
        raise ValueError("岗位没有可用于评分的requirement")

    total_weight = sum(
        requirement.weight
        for requirement in jd.requirements
    )

    # 返回requirement.id ：归一化后的权重
    # 方便之后直接按照requirement.id str查询
    if total_weight > 0:
        return {
            requirement.id: requirement.weight / total_weight
            for requirement in jd.requirements
        }

    equal_weight = 1 / len(jd.requirements)

    return {
        requirement.id: equal_weight
        for requirement in jd.requirements
    }

# 将发现证据转为内部业务证据，输出为list
# 注意这里的证据写在单条requirement里面，单条requirement有复数证据
# 之后要注意cha宝有没有搞错这一点
# 这里其实有问题：万一没有证据的时候怎么办...写入issue
def _build_match_evidence(
    llm_result,
    candidate: Candidate,
    location: str,
) -> tuple[list[MatchEvidence], list[EvidenceValidationIssue]]:
    """只把可从 Candidate 或 raw_text 精确确认的文本转为正式证据。"""

    verified: list[MatchEvidence] = []
    issues: list[EvidenceValidationIssue] = []

    for index, evidence in enumerate(llm_result.evidence):
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

        verified.append(MatchEvidence(
            text=evidence.text,
            source_type=check.source_type,
            source_index=check.source_index,
            verification_status=check.verification_status,
            source_path=check.source_path,
            locator_verified=check.locator_verified,
        ))

    return verified, issues

# 转换requriement，注意一个原则Authoritative Data Source / 权威数据源
# 就是只取模型能给的，而其他要从jdinfo中拿
def _build_requirement_results(
    jd: JDInfo,
    candidate: Candidate,
    llm_result: LLMJobMatchResult,
    normalized_weights: dict[str, float],
    analysis_language: AnalysisLanguage,
) -> list[RequirementMatchResult]:
    """将LLM逐条匹配结果转换为系统内部评分结果。"""

    requirement_map = {
        requirement.id: requirement
        for requirement in jd.requirements
    }

    results: list[RequirementMatchResult] = []

    for llm_match in llm_result.requirement_matches:
        requirement = requirement_map[llm_match.requirement_id]
        evidence, evidence_issues = _build_match_evidence(
            llm_match,
            candidate,
            f"requirement[{requirement.id}]",
        )
        support_gap = (
            not evidence
            and llm_match.status != MatchStatus.INSUFFICIENT_EVIDENCE
        )
        confidence = llm_match.confidence
        if support_gap:
            confidence = MatchConfidence.LOW
        elif evidence_issues and confidence == MatchConfidence.HIGH:
            confidence = MatchConfidence.MEDIUM

        messages = _SCORING_EVIDENCE_TEXT[analysis_language]
        missing_information = list(llm_match.missing_information)
        if support_gap and messages["missing"] not in missing_information:
            missing_information.append(messages["missing"])

        needs_raw_review = llm_match.needs_raw_review or support_gap
        raw_review_reason = (
            llm_match.raw_review_reason.strip()
            if llm_match.raw_review_reason
            and llm_match.raw_review_reason.strip()
            else None
        )
        if support_gap and not raw_review_reason:
            raw_review_reason = messages["review"]

        result = RequirementMatchResult(
            requirement_id=requirement.id,
            requirement_name=requirement.name,
            must_have=requirement.must_have,
            original_weight=requirement.weight,
            normalized_weight=normalized_weights[requirement.id],
            status=llm_match.status,
            score=llm_match.score,
            confidence=confidence,
            reason=(messages["unsupported_reason"] if support_gap else llm_match.reason),
            evidence=evidence,
            evidence_validation_issues=evidence_issues,
            missing_information=missing_information,
            needs_raw_review=needs_raw_review,
            raw_review_reason=raw_review_reason,
        )

        results.append(result)

    return results

# 聚合must_have，注意已经留好了语义判断和业务判断的空间
# 非常巧妙
# 要等传统业务硬规则判断汇总才能最终判断
def _build_must_have_summary(
    requirement_results: list[RequirementMatchResult],
) -> MustHaveSummary:
    """汇总所有硬性条件的满足情况。"""

    failed_ids: list[str] = []
    confirmation_ids: list[str] = []

    for result in requirement_results:
        if not result.must_have:
            continue

        if result.status == MatchStatus.NOT_MATCHED:
            failed_ids.append(result.requirement_id)

        elif result.status in {
            MatchStatus.PARTIALLY_MATCHED,
            MatchStatus.INSUFFICIENT_EVIDENCE,
        }:
            confirmation_ids.append(result.requirement_id)

    return MustHaveSummary(
        has_failure=bool(failed_ids),
        failed_requirement_ids=failed_ids,
        needs_confirmation=bool(confirmation_ids),
        confirmation_requirement_ids=confirmation_ids,
    )

# 计算岗位总分咯
def _calculate_job_match_score(
    requirement_results: list[RequirementMatchResult],
) -> float:
    """根据归一化权重计算最终岗位匹配分。"""

    score = sum(
        result.score * result.normalized_weight
        for result in requirement_results
    )

    return round(score, 2)


def _build_raw_review_summary(
    requirement_results: list[RequirementMatchResult],
) -> tuple[list[str], bool, list[str]]:
    """从逐条领域结果聚合缺失信息和原始简历回查状态。"""

    missing_information: list[str] = []
    seen_missing_information: set[str] = set()
    raw_review_requirement_ids: list[str] = []

    for result in requirement_results:
        for item in result.missing_information:
            normalized_item = item.strip()
            if (
                normalized_item
                and normalized_item not in seen_missing_information
            ):
                seen_missing_information.add(normalized_item)
                missing_information.append(normalized_item)

        if result.needs_raw_review:
            raw_review_requirement_ids.append(result.requirement_id)

    return (
        missing_information,
        bool(raw_review_requirement_ids),
        raw_review_requirement_ids,
    )


def _validate_job_match_result_consistency(
    job_match_result: JobMatchResult,
) -> None:
    """校验后端聚合结果中的核心业务不变量。"""

    requirement_ids = {
        result.requirement_id
        for result in job_match_result.requirement_results
    }
    raw_review_id_set = set(
        job_match_result.raw_review_requirement_ids
    )

    unknown_ids = raw_review_id_set - requirement_ids
    if unknown_ids:
        raise ValueError(
            "岗位匹配结果包含不存在的raw review requirement: "
            f"{sorted(unknown_ids)}"
        )

    expected_raw_review_ids = [
        result.requirement_id
        for result in job_match_result.requirement_results
        if result.needs_raw_review
    ]
    if (
        job_match_result.raw_review_requirement_ids
        != expected_raw_review_ids
    ):
        raise ValueError(
            "岗位匹配结果的raw review requirement汇总不一致"
        )

    if job_match_result.needs_raw_review != bool(expected_raw_review_ids):
        raise ValueError("岗位匹配结果的needs_raw_review汇总不一致")


def build_raw_review_requests(
    job_match_result: JobMatchResult,
) -> list[RawReviewRequest]:
    """根据领域评分结果构造未来编排层可消费的回查请求。"""

    requests: list[RawReviewRequest] = []

    for result in job_match_result.requirement_results:
        if not result.needs_raw_review:
            continue

        requests.append(
            RawReviewRequest(
                requirement_id=result.requirement_id,
                reason=result.raw_review_reason or result.reason,
                search_targets=list(result.missing_information),
            )
        )

    return requests

# 核心函数二：终极mapper
def _build_job_match_result(
    jd: JDInfo,
    candidate: Candidate,
    llm_result: LLMJobMatchResult,
    analysis_language: AnalysisLanguage,
) -> JobMatchResult:
    """将LLM岗位匹配结果转换为系统最终岗位匹配结果。"""

    normalized_weights = _normalize_requirement_weights(jd)

    requirement_results = _build_requirement_results(
        jd=jd,
        candidate=candidate,
        llm_result=llm_result,
        normalized_weights=normalized_weights,
        analysis_language=analysis_language,
    )

    must_have_summary = _build_must_have_summary(
        requirement_results
    )

    score = _calculate_job_match_score(
        requirement_results
    )

    (
        missing_information,
        needs_raw_review,
        raw_review_requirement_ids,
    ) = _build_raw_review_summary(requirement_results)

    has_evidence_issues = any(
        item.evidence_validation_issues
        for item in requirement_results
    )
    decisive_results = [
        item
        for item in requirement_results
        if item.status != MatchStatus.INSUFFICIENT_EVIDENCE
    ]
    all_decisive_results_lack_evidence = bool(decisive_results) and all(
        not item.evidence
        for item in decisive_results
    )
    overall_confidence = llm_result.overall_confidence
    if decisive_results and all(
        item.confidence == MatchConfidence.LOW
        for item in decisive_results
    ):
        overall_confidence = MatchConfidence.LOW
    elif has_evidence_issues and overall_confidence == MatchConfidence.HIGH:
        overall_confidence = MatchConfidence.MEDIUM

    result = JobMatchResult(
        job_id=jd.id,
        candidate_id=candidate.id,
        analysis_language=analysis_language,
        score=score,
        confidence=overall_confidence,
        requirement_results=requirement_results,
        must_have_summary=must_have_summary,
        missing_information=missing_information,
        needs_raw_review=needs_raw_review,
        raw_review_requirement_ids=raw_review_requirement_ids,
        summary=(
            _SCORING_EVIDENCE_TEXT[analysis_language]["unsupported_summary"]
            if all_decisive_results_lack_evidence
            else llm_result.summary
        ),
        warnings=(
            [_SCORING_EVIDENCE_TEXT[analysis_language]["warning"]]
            if has_evidence_issues
            else []
        ),
    )

    _validate_job_match_result_consistency(result)

    return result

# 正真的业务函数
# LLM结果 + Mapper
def evaluate_job_match(
    jd: JDInfo,
    candidate: Candidate,
    analysis_language: AnalysisLanguage,
) -> JobMatchResult:
    """完成候选人与岗位的完整岗位匹配评分。"""

    llm_result = evaluate_job_match_with_llm(
        jd=jd,
        candidate=candidate,
        analysis_language=analysis_language,
    )

    return _build_job_match_result(
        jd=jd,
        candidate=candidate,
        llm_result=llm_result,
        analysis_language=analysis_language,
    )
