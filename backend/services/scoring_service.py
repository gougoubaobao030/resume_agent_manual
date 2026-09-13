from clients.llm_client import LLMClient
from prompts.scoring_prompt import (
    JOB_MATCH_SYSTEM_PROMPT,
    build_job_match_user_prompt,
)
from schemas.jd import JDInfo
from schemas.resume import Candidate
from schemas.scoring import LLMJobMatchResult

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
    LLMJobMatchResult,
    MatchEvidence,
    MatchStatus,
    MustHaveSummary,
    RequirementMatchResult,
)


def _build_job_match_prompt(
    jd: JDInfo,
    candidate: Candidate,
) -> str:
    """将业务模型转换为岗位匹配Prompt输入。"""

    return build_job_match_user_prompt(
        jd_data=jd.model_dump(),
        candidate_data=candidate.model_dump(),
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
) -> LLMJobMatchResult:
    """使用LLM对结构化JD和结构化候选人进行岗位匹配判断。"""

    user_prompt = _build_job_match_prompt(
        jd=jd,
        candidate=candidate,
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
) -> list[MatchEvidence]:
    """将LLM证据DTO转换为系统内部证据模型。"""

    return [
        MatchEvidence(
            text=evidence.text,
            source_type=evidence.source_type,
            source_index=evidence.source_index,
        )
        for evidence in llm_result.evidence
    ]

# 转换requriement，注意一个原则Authoritative Data Source / 权威数据源
# 就是只取模型能给的，而其他要从jdinfo中拿
def _build_requirement_results(
    jd: JDInfo,
    llm_result: LLMJobMatchResult,
    normalized_weights: dict[str, float],
) -> list[RequirementMatchResult]:
    """将LLM逐条匹配结果转换为系统内部评分结果。"""

    requirement_map = {
        requirement.id: requirement
        for requirement in jd.requirements
    }

    results: list[RequirementMatchResult] = []

    for llm_match in llm_result.requirement_matches:
        requirement = requirement_map[llm_match.requirement_id]

        result = RequirementMatchResult(
            requirement_id=requirement.id,
            requirement_name=requirement.name,
            must_have=requirement.must_have,
            original_weight=requirement.weight,
            normalized_weight=normalized_weights[requirement.id],
            status=llm_match.status,
            score=llm_match.score,
            confidence=llm_match.confidence,
            reason=llm_match.reason,
            evidence=_build_match_evidence(llm_match),
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

# 核心函数二：终极mapper
def _build_job_match_result(
    jd: JDInfo,
    candidate: Candidate,
    llm_result: LLMJobMatchResult,
) -> JobMatchResult:
    """将LLM岗位匹配结果转换为系统最终岗位匹配结果。"""

    normalized_weights = _normalize_requirement_weights(jd)

    requirement_results = _build_requirement_results(
        jd=jd,
        llm_result=llm_result,
        normalized_weights=normalized_weights,
    )

    must_have_summary = _build_must_have_summary(
        requirement_results
    )

    score = _calculate_job_match_score(
        requirement_results
    )

    return JobMatchResult(
        job_id=jd.id,
        candidate_id=candidate.id,
        score=score,
        confidence=llm_result.overall_confidence,
        requirement_results=requirement_results,
        must_have_summary=must_have_summary,
        summary=llm_result.summary,
    )

# 正真的业务函数
# LLM结果 + Mapper
def evaluate_job_match(
    jd: JDInfo,
    candidate: Candidate,
) -> JobMatchResult:
    """完成候选人与岗位的完整岗位匹配评分。"""

    llm_result = evaluate_job_match_with_llm(
        jd=jd,
        candidate=candidate,
    )

    return _build_job_match_result(
        jd=jd,
        candidate=candidate,
        llm_result=llm_result,
    )