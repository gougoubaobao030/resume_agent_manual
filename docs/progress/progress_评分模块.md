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
- 完成LLM响应schema设计
- 有其他很多schema，主要schema为：
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

### update 完成二次审评Raw Review 预留 Schema
- 用于发现某关键分数低的有些可疑的时候，去原文找证据而非结构化简历并返回结果

### 2026年9月11日 完成scoring_prompt.py 并完成输出测试
- 内部prompt采用直接响应schema json注入
- 新增测试文件 scoring_integration_case.json
- 新增测试文件
- test_scoring_integration.py

## update 2026年9月14日
整体趋于完成状态
整体过程记录
## update 2026年9月8日~9月14日
# 已完成：岗位匹配评分模块 MVP 闭环

本阶段正式进入岗位匹配评分模块。

核心目标：

JDInfo
+
Candidate
↓
LLM语义匹配
↓
逐条 requirement 判断
↓
后端确定性聚合
↓
JobMatchResult
↓
FastAPI
↓
Vue 前端展示

本阶段坚持：

- LLM 负责自然语言语义判断
- 后端负责确定性业务逻辑和计算
- 不让 LLM 直接决定最终岗位总分
- 不把“简历没有写”直接判断为“不满足”
- 每个重要判断尽量保留理由和证据
- MVP 暂不实现真正的 raw resume 二次调用和 LangGraph
- 但 Schema 和 Service 为未来 orchestration 预留扩展点


--------------------------------------------------
## 1. 岗位匹配评分总体设计
--------------------------------------------------

评分最小单位确定为：

JDRequirement

不是直接让模型：

JD + Candidate
↓
输出一个总分

而是：

JDRequirement 1
JDRequirement 2
JDRequirement 3
...
↓
逐条语义判断
↓
RequirementMatchResult[]
↓
后端按照权重聚合
↓
JobMatchResult


单条岗位要求采用四种匹配状态：

- matched
- partially_matched
- not_matched
- insufficient_evidence

其中：

insufficient_evidence

用于表示：

当前候选人信息不足以判断。

核心原则：

“没有证据”
≠
“不满足”


--------------------------------------------------
## 2. must_have 与 weight 设计
--------------------------------------------------

JDRequirement 已增加：

must_have: bool

用于区分：

- 硬性 / 必须条件
- 普通要求 / 优先条件

同时保留：

weight

两者意义不同：

must_have：
表示是否属于必须条件。

weight：
表示该 requirement 对岗位核心胜任力的重要程度。

因此：

must_have=true
不代表
weight 必须很高。

岗位匹配阶段仍使用原始 weight，
后端评分时自动归一化。

如果所有 requirement weight 都为 0：

按等权处理。


--------------------------------------------------
## 3. scoring.py：评分 Domain Schema
--------------------------------------------------

新增：

backend/schemas/scoring.py


### 3.1 EvaluationLevel

用于后续：

- 潜力值
- 人材画像适配值

等级：

- high
- medium_high
- medium
- medium_low
- low
- needs_confirmation


### 3.2 MatchConfidence

用于表示当前判断的证据充分程度：

- high
- medium
- low

当前 confidence：

不是统计学概率，
不表示“90%一定正确”。

而是表示：

当前证据和判断是否充分。


### 3.3 MatchStatus

单条 requirement 的匹配状态：

- matched
- partially_matched
- not_matched
- insufficient_evidence


### 3.4 MatchEvidence

保存支持岗位匹配判断的事实证据。

字段：

- text
- source_type
- source_index

例如：

{
  "text": "使用FastAPI开发REST API",
  "source_type": "projects",
  "source_index": 0
}

设计目的：

Reason 和 Evidence 分离。

Reason：
系统 / 模型对事实的解释。

Evidence：
候选人简历中真实存在的事实。


--------------------------------------------------
## 4. RequirementMatchResult
--------------------------------------------------

用于保存：

候选人针对单条 JD requirement 的最终业务判断。

主要字段：

- requirement_id
- requirement_name
- must_have
- original_weight
- normalized_weight
- status
- score
- confidence
- reason
- evidence
- missing_information
- needs_raw_review
- raw_review_reason

其中：

original_weight：
HR / JD 保存的原始权重。

normalized_weight：
后端评分阶段归一化后的权重。

score：
当前 requirement 的直接匹配程度，0~100。

注意：

score 只表示岗位直接匹配程度，
不能偷偷加入：

- 潜力
- 成长性
- 人格
- 人材画像


--------------------------------------------------
## 5. MustHaveSummary
--------------------------------------------------

新增：

MustHaveSummary

用于聚合所有 must_have requirement。

核心状态：

- has_failure
- failed_requirement_ids
- needs_confirmation
- confirmation_requirement_ids

当前业务规则：

must_have + matched
→ 认为满足

must_have + not_matched
→ 明确失败

must_have + partially_matched
→ needs_confirmation

must_have + insufficient_evidence
→ needs_confirmation

原因：

硬性条件只有明确满足时才认为满足。

部分匹配或证据不足时，
MVP 不直接淘汰候选人，
交给 HR 进一步确认。


--------------------------------------------------
## 6. JobMatchResult
--------------------------------------------------

用于表示：

一名 Candidate 针对一个 JD 的最终岗位匹配结果。

主要字段：

- job_id
- candidate_id
- score
- confidence
- requirement_results
- must_have_summary
- missing_information
- needs_raw_review
- raw_review_requirement_ids
- summary

岗位总分：

由后端确定性计算：

Σ(
    requirement score
    ×
    normalized weight
)

最终：

round(score, 2)

注意：

即使 must_have 失败，
也不会把岗位匹配总分直接清零。

例如：

岗位匹配分：84
硬条件：日语N1未满足

系统会同时保留：

score = 84

和：

must_have_summary.has_failure = true

这样可以同时表达：

“整体能力匹配程度”

和：

“存在明确招聘硬障碍”

避免把所有业务信息压缩成一个数字。


--------------------------------------------------
## 7. 预留完整候选人评价总结构
--------------------------------------------------

为了后续扩展，但仍控制 MVP 范围，
scoring.py 中预留：

PotentialResult
TalentProfileResult
OpenDiscovery
FollowUpQuestion
CandidateEvaluationResult


### PotentialResult

用于未来证据潜力评价：

- level
- confidence
- summary
- evidence


### TalentProfileResult

用于未来人材画像：

- tags
- fit_level
- confidence
- summary
- evidence

注意：

人才画像只允许基于简历事实总结工作相关特征。

不做人格心理判断。


### OpenDiscovery

用于保存：

预设评分维度之外，
值得 HR 进一步关注的亮点。

当前倾向：

开放发现更适合作为结构化文字亮点，
不强制量化成 0~100。


### FollowUpQuestion

用于未来下一轮提问建议：

- question
- reason
- related_requirement_ids


### CandidateEvaluationResult

作为未来完整候选人评价聚合容器：

CandidateEvaluationResult
│
├ job_match
├ potential
├ talent_profile
├ open_discoveries
├ follow_up_questions
└ overall_summary

当前 MVP：

优先完成 job_match。

其他模块允许为空，
逐步实现。


--------------------------------------------------
## 8. LLM 专用岗位匹配 Schema
--------------------------------------------------

继续采用之前简历解析阶段的设计思想：

LLM DTO
≠
系统 Domain Model


新增：

LLMMatchEvidence
LLMRequirementMatch
LLMJobMatchResult


### LLMMatchEvidence

LLM 返回的证据 DTO。

虽然当前字段和 MatchEvidence 类似，
仍保持分离。

原因：

未来 LLM 输出结构变化，
不应该直接污染系统内部 Domain Model。


### LLMRequirementMatch

LLM 对单条 requirement 的语义判断。

字段：

- requirement_id
- status
- score
- confidence
- reason
- evidence
- missing_information
- needs_raw_review
- raw_review_reason


### LLMJobMatchResult

LLM 对整个岗位匹配的结构化输出。

字段：

- requirement_matches
- overall_confidence
- summary
- missing_information
- needs_raw_review
- raw_review_requirement_ids

注意：

LLMJobMatchResult 不输出最终岗位总分。

最终加权总分由后端计算。


--------------------------------------------------
## 9. Raw Resume Review 扩展点
--------------------------------------------------

未来希望增加：

当结构化 Candidate 对某个关键 requirement 证据不足时，
Agent 可以主动回查 Candidate.raw_text，
再进行二次判断。

当前尚未决定未来使用：

方案 A：
needs_raw_review 驱动普通 Python 二次调用

方案 B：
LLM Tool Calling

方案 C：
LangGraph conditional edge

因此当前只预留业务接口，
不绑定具体 orchestration 框架。


新增 Schema：

RawReviewRequest
RawReviewResult
RawReviewBatchResult


### RawReviewRequest

表示：

“为什么需要回查原始简历，
以及要寻找什么信息”。

字段：

- requirement_id
- reason
- search_targets


### RawReviewResult

表示：

回查原始简历后的结果。

字段包括：

- requirement_id
- found_relevant_information
- evidence
- updated_status
- updated_score
- updated_confidence
- reason
- remaining_missing_information


核心原则：

业务 Schema 不依赖 LangGraph。

未来：

普通 Python
Tool Calling
LangGraph

都可以使用相同业务模型。

设计思想：

Framework-agnostic Design。


--------------------------------------------------
## 10. scoring_prompt.py：岗位匹配 Prompt
--------------------------------------------------

新增：

backend/prompts/scoring_prompt.py


Prompt 采用：

业务规则
+
完整 JSON Schema
+
Pydantic 最终校验

的方式。


原因：

之前简历解析阶段曾出现：

DeepSeek 将本应为 list 的字段自由输出成 dict，

导致 Pydantic 校验失败。

因此岗位匹配 Prompt 加强结构约束。


### JSON Schema 自动生成

使用：

LLMJobMatchResult.model_json_schema()

自动生成 JSON Schema，

再通过：

json.dumps(...)

注入 Prompt。


设计思想：

Schema-driven LLM Integration

即：

Pydantic Model
↓
自动生成 JSON Schema
↓
Prompt约束
↓
LLM输出
↓
Pydantic再次校验


这样：

Pydantic Schema

成为唯一结构事实来源。

避免：

Prompt 手写字段

和：

真实代码 Schema

发生漂移。


Prompt 明确要求：

- requirement_matches 必须是 list
- evidence 必须是 list
- missing_information 必须是 list
- raw_review_requirement_ids 必须是 list
- 不得遗漏 requirement
- 不得生成不存在的 requirement_id
- 不得增加 Schema 不存在的字段
- 只输出合法 JSON
- 输出最终会被 Pydantic 校验


--------------------------------------------------
## 11. scoring_service.py：岗位匹配 Service
--------------------------------------------------

新增：

backend/services/scoring_service.py


核心流程：

JDInfo
+
Candidate
↓
_build_job_match_prompt()
↓
DeepSeek
↓
LLMJobMatchResult
↓
_validate_requirement_coverage()
↓
_normalize_requirement_weights()
↓
_build_requirement_results()
↓
_build_must_have_summary()
↓
_calculate_job_match_score()
↓
JobMatchResult


--------------------------------------------------
## 12. _build_job_match_prompt()
--------------------------------------------------

作用：

将：

JDInfo
Candidate

转换为 Prompt 所需输入。

内部使用：

jd.model_dump()
candidate.model_dump()

再交给：

build_job_match_user_prompt()


设计目的：

把：

业务模型输入准备

和：

LLM 调用

分开。

未来如果 Candidate 太大，
需要减少传入模型字段，
只修改该输入准备逻辑即可。


--------------------------------------------------
## 13. evaluate_job_match_with_llm()
--------------------------------------------------

职责：

执行一次真实 LLM 岗位匹配判断。

流程：

JDInfo + Candidate
↓
Prompt
↓
LLMClient.generate_structured()
↓
LLMJobMatchResult
↓
requirement coverage 校验

返回：

LLMJobMatchResult

该函数主要用于：

- 模型调用
- 调试
- 查看原始 LLM DTO

不负责：

- 权重计算
- must_have 聚合
- 最终岗位总分


--------------------------------------------------
## 14. _validate_requirement_coverage()
--------------------------------------------------

作用：

检查 LLM 是否：

完整且唯一地评价了所有 JD requirements。

检查：

1. requirement_id 是否重复
2. 是否缺少 requirement
3. 是否出现不存在的 requirement_id

设计原因：

Pydantic 只负责结构校验。

例如：

requirement_matches 少一条，

JSON 结构仍然完全合法，
Pydantic 无法发现。

因此增加：

Business Validation

形成三层防御：

Prompt
↓
结构要求

Pydantic
↓
Structural Validation

scoring_service
↓
Business Validation


--------------------------------------------------
## 15. _normalize_requirement_weights()
--------------------------------------------------

作用：

将 JD requirement 原始权重归一化。

例如：

Python = 10
FastAPI = 5

变为：

Python = 0.6667
FastAPI = 0.3333

如果全部 weight = 0：

自动等权。

返回：

dict[requirement_id, normalized_weight]


--------------------------------------------------
## 16. _build_match_evidence()
--------------------------------------------------

作用：

LLMMatchEvidence
↓
MatchEvidence

即：

LLM DTO
↓
Domain Model

设计思想：

Mapper / Assembler

避免 LLM DTO 直接进入业务模型。


--------------------------------------------------
## 17. _build_requirement_results()
--------------------------------------------------

作用：

将所有：

LLMRequirementMatch

转换为：

RequirementMatchResult


从 LLM 获取：

- status
- score
- confidence
- reason
- evidence
- missing_information
- needs_raw_review
- raw_review_reason


从真实 JD 获取：

- requirement_name
- must_have
- original_weight
- normalized_weight


核心原则：

业务权威字段始终来自：

JDInfo

而不是相信 LLM 再复制一次。

设计思想：

Authoritative Data Source。


--------------------------------------------------
## 18. _build_must_have_summary()
--------------------------------------------------

作用：

根据：

RequirementMatchResult[]

汇总 must_have 状态。

规则：

matched
→ 满足

not_matched
→ failed

partially_matched
→ needs_confirmation

insufficient_evidence
→ needs_confirmation


LLM 不直接决定：

hard_requirement_failed。

后端根据：

must_have
+
MatchStatus

自己确定性计算。


--------------------------------------------------
## 19. _calculate_job_match_score()
--------------------------------------------------

作用：

后端计算岗位总分。

公式：

Σ(
    requirement.score
    ×
    requirement.normalized_weight
)

最后：

round(score, 2)

核心设计：

LLM负责语义判断。

后端负责算术。

即：

Probabilistic AI
+
Deterministic Software


--------------------------------------------------
## 20. _build_job_match_result()
--------------------------------------------------

作用：

将：

LLMJobMatchResult

正式转换为：

JobMatchResult


主要完成：

- 权重归一化
- requirement Domain Model 构造
- must_have 聚合
- 总分计算
- confidence / summary 保存
- missing_information 聚合
- raw review 状态聚合


--------------------------------------------------
## 21. evaluate_job_match()
--------------------------------------------------

这是当前真正给业务层调用的岗位匹配函数。

流程：

evaluate_job_match()
↓
evaluate_job_match_with_llm()
↓
LLMJobMatchResult
↓
_build_job_match_result()
↓
JobMatchResult

最终返回：

系统真实业务岗位匹配结果。


--------------------------------------------------
## 22. Raw Review 信息保留与连接点
--------------------------------------------------

Step 4-E 已补充：

LLMRequirementMatch 中的：

- missing_information
- needs_raw_review
- raw_review_reason

在：

LLM DTO
↓
RequirementMatchResult
↓
JobMatchResult

转换过程中不再丢失。


新增逻辑：

根据 RequirementMatchResult
后端自己聚合：

- JobMatchResult.needs_raw_review
- raw_review_requirement_ids
- missing_information


不直接信任：

LLMJobMatchResult 顶层聚合状态。


新增公开函数：

build_raw_review_requests()

作用：

JobMatchResult
↓
找出 needs_raw_review=True 的 requirement
↓
RawReviewRequest[]


当前只生成 Request。

尚未真正：

- 查询 raw_text
- 二次调用 LLM
- 更新评分


--------------------------------------------------
## 23. Step 4-F：必要业务一致性校验
--------------------------------------------------

补充轻量防御性校验和容错。

原则：

只处理真正可能影响业务正确性的情况。

不因为 LLM 少输出一个辅助信息，
导致整份候选人评分失败。


避免过度严格，例如：

不强制：

matched
必须 evidence 非空
否则报错。

不强制：

confidence=low
不能 matched。

不强制：

所有 missing_information
都必须触发 raw review。


目标：

在保证核心业务正确性的前提下，
提高 LLM 输出容错性。


--------------------------------------------------
## 24. Step 4-E / 4-F 教学文档
--------------------------------------------------

由于项目时间被压缩到约10天，

Step 4-E / 4-F 实现交由 Codex 完成，

并要求生成详细教学文档：

docs/scoring_step_4e_4f_tutorial.md

用于之后补学。

文档内容包括：

- 每个函数用途
- DTO vs Domain Model
- Mapper
- Aggregation
- Business Validation
- Structural Validation
- State-driven Orchestration
- Framework-agnostic Design
- 普通 Python / Tool Calling / LangGraph 未来接入方式


--------------------------------------------------
## 25. 岗位匹配 API
--------------------------------------------------

新增：

POST /api/scoring/job-match


请求结构：

{
  "job_id": "...",
  "candidate": {...}
}


设计：

前端只传：

job_id
+
Candidate

后端根据：

job_id

从已有：

jd_repository

获取 HR 已确认保存的正式 JD。

不要求前端再次提交整份 JD。


原因：

避免：

前端 JD

和：

后端正式保存 JD

出现不一致。


API 流程：

HTTP Request
↓
job_id
↓
jd_repository.get_jd()
↓
JDInfo
+
Candidate
↓
evaluate_job_match()
↓
JobMatchResult
↓
HTTP JSON


异常继续沿用：

- LLMConfigError
- LLMRequestError
- LLMResponseError
- ValueError / 业务错误


--------------------------------------------------
## 26. 真实岗位匹配测试已通过
--------------------------------------------------

测试：

AI应用开发工程师 JD
+
candidate_966ab016

得到：

岗位匹配总分：

94.43

confidence：

high


requirement 包括：

- Python开发经验
- 学历要求
- 后端开发经验
- LLM应用经验
- 完整项目经验
- 日语能力


所有 requirement：

成功逐条生成：

- status
- score
- confidence
- reason
- evidence
- missing_information
- raw review 状态


must_have：

Python开发经验
→ matched

本科及以上
→ matched


must_have_summary：

has_failure = false

needs_confirmation = false


LLM应用经验：

模型正确识别：

候选人有明确 LLM 应用开发经验，

同时指出：

未明确提供 RAG 专项开发经验的具体证据。


最终：

missing_information：

[
  "未明确提供RAG专项开发经验的具体证据"
]


needs_raw_review：

false


测试说明：

- LLMJobMatchResult 成功通过 Pydantic
- requirement_matches 正确保持 list
- requirement coverage 校验通过
- normalized_weight 正常
- 最终 score 正常聚合
- must_have 正常聚合
- Evidence 正常保留
- missing_information 正常保留


--------------------------------------------------
## 27. Vue 前端岗位匹配接入
--------------------------------------------------

岗位匹配后端跑通后，

Vue 前端继续保持：

backend/ 零修改

根据真实后端 JobMatchResult 接入展示。


修改：

frontend/src/services/api.js
frontend/src/state/session.js
frontend/src/views/ResumeUploadView.vue
frontend/src/views/CandidateListView.vue
frontend/src/views/CandidateDetailView.vue
frontend/src/views/AnalysisResultView.vue
frontend/src/styles/main.css
frontend/src/layouts/AppLayout.vue
frontend/src/views/DashboardView.vue


--------------------------------------------------
## 28. Vue API 接入
--------------------------------------------------

api.js：

接入真实接口：

POST /api/scoring/job-match


请求：

{
  "job_id": "...",
  "candidate": {...}
}


ResumeUploadView：

简历解析完成后，
调用真实岗位匹配评分接口。


session.js：

按 candidate 保存：

- 评分结果
- loading 状态
- error 状态


--------------------------------------------------
## 29. 候选人列表展示
--------------------------------------------------

CandidateListView：

主列表只显示 HR 最需要快速查看的信息：

- 候选人姓名
- 岗位匹配分
- must_have 状态
- summary


must_have 状态：

has_failure = true
→ 硬条件不满足

否则：

needs_confirmation = true
→ 硬条件需确认

否则：

→ 硬条件满足


confidence 不作为列表主视觉。


--------------------------------------------------
## 30. 候选人详情 / 分析结果展示
--------------------------------------------------

CandidateDetailView / AnalysisResultView：

展示：

- 岗位匹配分
- summary
- must_have 状态
- requirement_name
- must_have
- status
- score
- confidence
- reason
- evidence
- missing_information
- needs_raw_review
- raw_review_reason


status 前端转换为人类可读文本：

matched
→ 满足

partially_matched
→ 部分满足

not_matched
→ 不满足

insufficient_evidence
→ 证据不足


confidence：

- high → 高
- medium → 中
- low → 低

confidence 只作为次要辅助信息展示，
不作为主视觉指标。


--------------------------------------------------
## 31. Evidence 前端展示
--------------------------------------------------

每条 evidence 展示：

- text

source_type / source_index：

作为辅助来源信息显示。

例如：

来源：项目经历 #1


核心目标：

让 HR 不只是看到：

“AI说匹配”

而是能够看到：

“为什么匹配，
证据具体来自哪里”。


--------------------------------------------------
## 32. 前端刻意不展示的字段
--------------------------------------------------

当前不重点展示：

顶层 confidence

原因：

避免模型自评可信度成为主视觉。


不展示：

original_weight
normalized_weight

原因：

属于评分技术细节，
当前 HR 主页面不需要。


不展示：

job_id
candidate_id

原因：

内部关联字段。


不直接展示：

failed_requirement_ids
confirmation_requirement_ids
raw_review_requirement_ids

原因：

页面已经通过总体状态和具体 requirement 内容表达，
直接显示内部 ID 会增加技术噪音。


--------------------------------------------------
## 33. Vue 验证
--------------------------------------------------

执行：

npm run build

结果：

成功。

示例：

✓ 35 modules transformed.
✓ built successfully


本次 Vue 接入：

backend/ 未做任何修改。


--------------------------------------------------
# 当前岗位匹配模块完整流程
--------------------------------------------------

HR确认并保存JD
↓
JDInfo

Candidate结构化简历
↓
Candidate

JDInfo + Candidate
↓
POST /api/scoring/job-match
↓
scoring_service
↓
岗位匹配 Prompt
↓
DeepSeek
↓
LLMJobMatchResult
↓
Pydantic结构校验
↓
requirement coverage业务校验
↓
LLM DTO → Domain Model
↓
weight归一化
↓
must_have聚合
↓
后端确定性计算总分
↓
raw review状态聚合
↓
JobMatchResult
↓
Vue
↓
候选人列表
+
候选人详情
+
完整评分依据


--------------------------------------------------
# 当前岗位匹配模块状态
--------------------------------------------------

已完成：

✅ 岗位匹配 Domain Schema

✅ LLM 专用评分 Schema

✅ JSON Schema 自动注入 Prompt

✅ DeepSeek 真实语义评分

✅ Pydantic 输出校验

✅ Requirement Coverage 防御性校验

✅ 每条 requirement 匹配状态

✅ Requirement Score

✅ Evidence

✅ Confidence

✅ Missing Information

✅ Must-have 三态处理

✅ Weight 自动归一化

✅ 后端确定性总分

✅ Raw Review 扩展点

✅ RawReviewRequest 构造接口

✅ FastAPI 岗位匹配接口

✅ Vue 前端真实接口接入

✅ 候选人列表评分展示

✅ 候选人详情评分证据展示

✅ npm build 验证成功


暂未实现：

- 真正 Raw Resume 二次回查
- Tool Calling
- LangGraph orchestration
- Confidence Aggregator
- 潜力值真实评分逻辑
- 人材画像真实评分逻辑
- 开放发现逻辑
- 下一轮提问生成逻辑
- 评分历史数据库


这些属于后续模块 / MVP增强，
不影响当前岗位匹配评分闭环。


--------------------------------------------------
# 本阶段关键设计思想
--------------------------------------------------

1. LLM DTO 与 Domain Model 分离

2. 模型负责语义判断，程序负责确定性计算

3. Pydantic 负责 Structural Validation

4. Service 负责 Business Validation

5. Requirement 是岗位匹配评分最小原子单位

6. “没有证据”不等于“不满足”

7. must_have 与 weight 分离

8. 总分由后端计算，不让 LLM 自行聚合

9. Evidence 与 Reason 分离

10. Schema-driven LLM Integration

11. Authoritative Data Source

12. Mapper / Assembler

13. Aggregation

14. Framework-agnostic Design

15. 为 LangGraph / Tool Calling 预留接口，
    但 MVP 不提前引入复杂编排框架

16. 前端优先展示 HR 真正需要的信息，
    不把技术字段堆成 AI Demo


--------------------------------------------------
# 下一阶段
--------------------------------------------------

岗位匹配评分模块 MVP 已完成闭环。

下一步进入：

证据潜力评价模块

重点：

Candidate
+
岗位匹配中的缺口
+
candidate_evidence
+
项目 / 工作 / 学习事实

↓

判断候选人是否存在：

- 技能迁移证据
- 学习并落地证据
- 持续成长证据
- 非标准路径成果
- 可补偿岗位缺口的相关经验

↓

PotentialResult

当前仍坚持：

先完成单份候选人的可靠评价，
再考虑复杂 Agent orchestration。