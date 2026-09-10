from enum import Enum
from pydantic import BaseModel, Field


class EvaluationLevel(str, Enum):
    """用于潜力值、人材像适配值等等级型评价。"""

    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    MEDIUM_LOW = "medium_low"
    LOW = "low"
    NEEDS_CONFIRMATION = "needs_confirmation"


class MatchConfidence(str, Enum):
    """表示当前匹配判断的可信程度。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MatchStatus(str, Enum):
    """单条岗位要求的语义匹配状态。"""

    MATCHED = "matched"
    PARTIALLY_MATCHED = "partially_matched"
    NOT_MATCHED = "not_matched"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class MatchEvidence(BaseModel):
    """支持评分判断的候选人事实证据。"""

    text: str = Field(..., min_length=1)
    source_type: str | None = None
    source_index: int | None = Field(default=None, ge=0)

#单条汇总 硬条件评价
class RequirementMatchResult(BaseModel):
    """候选人针对单条 JD requirement 的匹配结果。"""

    requirement_id: str
    requirement_name: str

    must_have: bool = False

    original_weight: float = Field(
        ...,
        ge=0,
    )

    normalized_weight: float = Field(
        ...,
        ge=0,
        le=1,
    )

    status: MatchStatus

    score: float = Field(
        ...,
        ge=0,
        le=100,
    )

    confidence: MatchConfidence

    reason: str

    evidence: list[MatchEvidence] = Field(
        default_factory=list
    )

#硬条件哪几个不对，哪几个需要确认
class MustHaveSummary(BaseModel):
    """岗位硬性条件的总体判断结果。"""

    has_failure: bool = False

    failed_requirement_ids: list[str] = Field(
        default_factory=list
    )

    needs_confirmation: bool = False

    confirmation_requirement_ids: list[str] = Field(
        default_factory=list
    )

#岗位评分总结果
class JobMatchResult(BaseModel):
    """一名候选人针对一个岗位的岗位匹配结果。"""

    job_id: str
    candidate_id: str

    score: float = Field(
        ...,
        ge=0,
        le=100,
    )

    confidence: MatchConfidence

    requirement_results: list[RequirementMatchResult] = Field(
        default_factory=list
    )

    must_have_summary: MustHaveSummary = Field(
        default_factory=MustHaveSummary
    )

    summary: str | None = None

# 其他各项分数
class PotentialResult(BaseModel):
    """候选人的证据潜力评价结果。"""

    level: EvaluationLevel
    confidence: MatchConfidence
    summary: str

    evidence: list[MatchEvidence] = Field(
        default_factory=list
    )


class TalentProfileResult(BaseModel):
    """基于简历事实形成的人材画像及其适配结果。"""

    tags: list[str] = Field(
        default_factory=list
    )

    fit_level: EvaluationLevel | None = None

    confidence: MatchConfidence | None = None

    summary: str | None = None

    evidence: list[MatchEvidence] = Field(
        default_factory=list
    )


class OpenDiscovery(BaseModel):
    """预设评分维度之外值得HR进一步关注的候选人亮点。"""

    title: str
    description: str

    evidence: list[MatchEvidence] = Field(
        default_factory=list
    )


class FollowUpQuestion(BaseModel):
    """建议HR在下一轮沟通中进一步确认的问题。"""

    question: str
    reason: str

    related_requirement_ids: list[str] = Field(
        default_factory=list
    )


class CandidateEvaluationResult(BaseModel):
    """候选人针对某岗位的一次完整评价结果。"""

    job_id: str
    candidate_id: str

    job_match: JobMatchResult

    potential: PotentialResult | None = None

    talent_profile: TalentProfileResult | None = None

    open_discoveries: list[OpenDiscovery] = Field(
        default_factory=list
    )

    follow_up_questions: list[FollowUpQuestion] = Field(
        default_factory=list
    )

    overall_summary: str | None = None


# --------------LLM 模型模型响应 SCHEMA----------------------
class LLMMatchEvidence(BaseModel):
    """LLM返回的候选人匹配证据。"""

    text: str = Field(..., min_length=1)

    source_type: str | None = None

    source_index: int | None = Field(
        default=None,
        ge=0,
    )

class LLMRequirementMatch(BaseModel):
    """LLM对单条岗位要求的语义匹配判断。"""

    requirement_id: str

    status: MatchStatus

    score: float = Field(
        ...,
        ge=0,
        le=100,
    )

    confidence: MatchConfidence

    reason: str

    evidence: list[LLMMatchEvidence] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    needs_raw_review: bool = False

    raw_review_reason: str | None = None

class LLMJobMatchResult(BaseModel):
    """LLM对候选人与岗位整体匹配情况的结构化判断结果。"""

    requirement_matches: list[LLMRequirementMatch] = Field(
        default_factory=list
    )

    overall_confidence: MatchConfidence

    summary: str

    missing_information: list[str] = Field(
        default_factory=list
    )

    needs_raw_review: bool = False

    raw_review_requirement_ids: list[str] = Field(
        default_factory=list
    )

#--------------- Raw Review 预留 Schema
class RawReviewRequest(BaseModel):
    """针对单条岗位要求的原始简历回查请求。"""

    requirement_id: str

    reason: str

    search_targets: list[str] = Field(
        default_factory=list
    )


class RawReviewResult(BaseModel):
    """基于原始简历文本进行二次回查后的结果。"""

    requirement_id: str

    found_relevant_information: bool = False

    evidence: list[LLMMatchEvidence] = Field(
        default_factory=list
    )

    updated_status: MatchStatus | None = None

    updated_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    updated_confidence: MatchConfidence | None = None

    reason: str

    remaining_missing_information: list[str] = Field(
        default_factory=list
    )


class RawReviewBatchResult(BaseModel):
    """一次原始简历回查阶段的汇总结果。"""

    results: list[RawReviewResult] = Field(
        default_factory=list
    )

