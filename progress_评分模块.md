## update 2026年9月7日
* JD requirement 新增 `must_have` 字段，用于区分硬性条件与普通加分/优先条件。
* 调整 JD 解析 Prompt，明确区分 `must_have` 与 `weight`：硬性条件不等于高权重，权重仍表示该条件对岗位核心胜任力的重要程度。
* 原“伯乐分”暂定调整为“人材画像匹配分”，用于评价候选人与企业/岗位期望人才画像之间的匹配程度。

## update 2026年9月9日
- 已完成潜力匹配分schema设计
```
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
```
- score 暂定有可信度评分
- 潜力分 暂定 高 中高 中 中低 低

## update 重要设计更新
- 为了显示真正的智能化,我们在结构化简历证据不足时，大模型能自己判断去查原文。
- 匹配评分模块将预留“证据不足时回查原始简历并二次判断”的能力，当前先在 LLM 响应中表达证据充分性、缺失证据和证据来源，不绑定 need_raw_data 或 tool calling 的具体实现。
- 架构上提前解耦单次 LLM 调用与整体评分流程，未来引入 LangGraph 时主要新增 orchestration 编排层，尽量避免重写现有 schema、service 和评分逻辑。

## update 
- 完成LLM影响schema设计
- 有其他很多schema，主要scheema为：
```
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
```
- 完成 Raw Review 预留 Schema
- 主要schema为以下内容
```
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

```

