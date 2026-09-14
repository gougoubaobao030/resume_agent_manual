# 岗位匹配评分 Step 4-E / 4-F 教学笔记

## 1. 这一步在解决什么问题

当前岗位匹配的第一次判断只使用结构化 `Candidate`。结构化信息适合稳定评分，但解析过程可能压缩或遗漏原始简历中的细节。例如，候选人的项目描述可能提到“检索、向量库、召回”，结构化结果却只保留“AI 项目”。这时 LLM 可以判断“证据不足，值得回查原文”，但如果 Mapper 没有把相关字段带进 Domain Model，这个信号会在 DTO 转换后消失。

Step 4-E 的作用，是让以下状态穿过完整的业务数据流：

- 当前缺少什么信息；
- 哪条 requirement 值得回查原始简历；
- 为什么值得回查；
- 如果未来编排层决定回查，应向它提供什么请求。

本步骤只建立连接点，不读取原始简历，也不进行第二次 LLM 调用。

Step 4-F 的作用，是把真正属于后端的确定性规则守住。LLM 负责语义判断，但不能成为 requirement 权重、硬条件汇总、最终总分和顶层 raw-review 状态的权威来源。后端应从逐条结果重新计算这些内容，同时对核心业务不变量做防御性校验。

## 2. 修改文件

### `backend/schemas/scoring.py`

`RequirementMatchResult` 新增：

- `missing_information: list[str]`
- `needs_raw_review: bool`
- `raw_review_reason: str | None`

`JobMatchResult` 新增：

- `missing_information: list[str]`
- `needs_raw_review: bool`
- `raw_review_requirement_ids: list[str]`

这些字段原来已经存在于 LLM DTO，但不存在于最终 Domain Model，因此此前转换时会丢失。`RawReviewRequest` 等预留 Schema 已存在，本次没有重复创建。

### `backend/services/scoring_service.py`

Mapper 现在保留 requirement 级 raw-review 信息，并新增后端聚合、业务一致性校验和 `RawReviewRequest` 构造函数。

API、Prompt、LLM Client、数据库和其他业务模块均未修改。

## 3. 函数逐个讲解

### 修改：`_build_requirement_results`

- 输入：`JDInfo`、`LLMJobMatchResult`、归一化权重字典。
- 输出：`list[RequirementMatchResult]`。
- 职责：将每个 `LLMRequirementMatch` 映射为领域结果；语义判断字段取自 LLM，名称、是否硬条件、原始权重和归一化权重取自 JD 这个权威数据源。
- 本次变化：继续复制 `missing_information`、`needs_raw_review` 和 `raw_review_reason`。纯空白的 `raw_review_reason` 被规范化为 `None`。
- 为什么需要：否则 LLM 的回查建议在 DTO 到 Domain 的边界上会丢失。
- 不能负责：不能决定是否真的进行回查，不能调用 LLM，也不能计算整个岗位的最终分数。

### 新增：`_build_raw_review_summary`

- 输入：`list[RequirementMatchResult]`。
- 输出：三元组 `(missing_information, needs_raw_review, raw_review_requirement_ids)`。
- 职责：从逐条领域结果聚合顶层 raw-review 状态；汇总并去重缺失信息；按照原有出现顺序保留第一次出现的非空文本；只把 `needs_raw_review=True` 的 requirement ID 放入回查 ID 列表。
- 为什么需要：顶层状态必须是逐条业务结果的确定性投影，不能直接信任 LLM 顶层字段。
- 不能负责：不能改变 requirement 的语义结论，不能访问原始简历，不能决定编排是否继续。

### 新增：`_validate_job_match_result_consistency`

- 输入：`JobMatchResult`。
- 输出：无；发现核心不一致时抛出 `ValueError`。
- 职责：确认顶层 raw-review ID 都来自真实 `requirement_results`；确认 ID 列表及顶层布尔值与 requirement 级状态一致。
- 为什么需要：这是后端自己产生的数据，若不一致通常意味着 Mapper 或后续维护代码出现缺陷，应尽早暴露。
- 不能负责：不会因为 evidence 为空、confidence 较低或辅助说明缺失而拒绝整份评分，也不替代 Pydantic 的数值范围校验。

### 新增（公开）：`build_raw_review_requests`

- 输入：一个已经完成后端聚合的 `JobMatchResult`。
- 输出：`list[RawReviewRequest]`。
- 职责：遍历 `requirement_results`，只为 `needs_raw_review=True` 的条目创建请求。`requirement_id` 来自该领域结果；`reason` 优先使用 `raw_review_reason`，缺失时退回普通 `reason`；`search_targets` 来自 `missing_information`。
- 为什么需要：它把“评分结果”变成“未来编排可以消费的下一步输入”，但不绑定任何编排框架。
- 不能负责：不查询 `Candidate.raw_text`，不调用 LLM，不合并二次回查结果，也不自动启动下一阶段。

### 修改：`_build_job_match_result`

- 输入：`JDInfo`、`Candidate`、`LLMJobMatchResult`。
- 输出：最终 `JobMatchResult`。
- 职责：编排本模块内的确定性步骤，包括权重归一化、逐条映射、must-have 汇总、加权总分计算、raw-review 聚合和结果一致性校验。
- 本次变化：调用 `_build_raw_review_summary`，把聚合结果写入 Domain Model，构造完成后调用 `_validate_job_match_result_consistency`。
- 为什么需要：这里是 LLM DTO 转为最终岗位匹配领域结果的总入口。
- 不能负责：不能执行未来的 raw resume review，也不能承担 API 序列化或工作流框架职责。

## 4. Step 4-F 的规则分级

### A. 强制抛异常

适合强制失败的是破坏核心结构或权威数据边界的情况：

- LLM 对 requirement 有遗漏、重复或返回未知 ID；现有 `_validate_requirement_coverage` 已负责。
- 后端最终结果中的 `raw_review_requirement_ids` 引用了不存在的 requirement。
- 顶层 raw-review 布尔值或 ID 列表与逐条领域状态不一致。
- `score` 不在 0～100、`normalized_weight` 不在 0～1；这些已由 Pydantic 字段约束负责，无需 Service 重复实现。

### B. 容错或规范化

以下属于辅助信息瑕疵，不应拖垮批量评分：

- `needs_raw_review=True` 但 `missing_information` 为空：保留 review 状态，生成空的 `search_targets`。
- `raw_review_reason` 为空或只有空白：规范化为 `None`；构造请求时回退到该 requirement 的普通 `reason`。
- 顶层 LLM `needs_raw_review`、`raw_review_requirement_ids` 或 `missing_information` 与逐条结果不一致：不报错，也不信任它们；后端从 `requirement_results` 重新聚合。
- 汇总缺失信息时：去掉空白项并去重，尽量保持原顺序。

### C. 暂时不限制

MVP 刻意不建立这些过度严格规则：

- `MATCHED` 必须有 evidence；
- `confidence=low` 时禁止 `MATCHED`；
- 只要存在 `missing_information` 就必须 raw review；
- `needs_raw_review=True` 时必须同时具备非空缺失信息和专用回查原因。

这些条件可以作为质量监控信号，但不适合让一份候选人评分整体失败。

## 5. 核心概念

### DTO vs Domain Model

DTO（Data Transfer Object）描述某个系统边界传输的数据。本项目中的 `LLMRequirementMatch` 和 `LLMJobMatchResult` 是 LLM 输出 DTO：它们允许模型表达语义判断和回查建议。

Domain Model 描述业务内部认可的事实和结果。`RequirementMatchResult` 和 `JobMatchResult` 是领域模型：除了承接 LLM 判断，还包含 JD 权威字段、后端归一化权重、确定性总分和硬条件汇总。

二者分离的意义是：LLM 返回什么，不等于系统最终相信什么。

### Mapper

Mapper 是模型之间的翻译层。`_build_requirement_results` 和 `_build_job_match_result` 负责 DTO → Domain。Mapper 不只是复制字段，还要选择权威数据源：例如 requirement 名称、权重和 `must_have` 必须来自 JD，而不是由 LLM 编造。

### Aggregation

Aggregation 是从多个子结果计算整体状态。本模块有三类典型聚合：

- requirement 分数 × normalized weight 得到最终总分；
- must-have requirement 的状态得到失败项和待确认项；
- requirement 级回查状态得到顶层 `needs_raw_review` 和 ID 列表。

### Business Validation

业务校验关注“数据在业务上是否自洽”。例如 raw-review ID 必须指向真实 requirement，顶层聚合状态必须与逐条状态一致。这类规则无法仅靠字段类型表达。

### Structural Validation vs Business Validation

结构校验回答“形状和范围是否合法”，例如字段是否为 list、score 是否在 0～100。Pydantic 擅长这一层。

业务校验回答“多个合法字段组合起来是否仍然合理”，例如顶层 ID 是否来自逐条结果。Service 负责这一层。两者互补，不应重复堆砌相同检查。

### State-driven Orchestration

状态驱动编排不是让评分函数立即执行下一步，而是让结果显式携带状态。编排层看到 `JobMatchResult.needs_raw_review=True` 后，才决定是否构造请求、读取原文和调用工具。这样每一步的输入输出都可观察、可测试。

### Framework-agnostic Design

`build_raw_review_requests(job_match_result)` 只接收 Pydantic 业务模型并返回 Pydantic 请求模型，不依赖 LangGraph、Tool Calling SDK 或 Web 框架。因此未来更换编排方式时，评分领域模型和 Service 不需要重写。

## 6. 为什么“LLM 提议，Orchestration 决定”

LLM 最适合发现语义上的不确定性，所以它可以对某条 requirement 设置 `needs_raw_review=True`。但是否真的回查还涉及成本、批量任务策略、候选人优先级、超时、人工审核策略以及原文是否可用，这些不是单条语义判断应决定的。

因此职责应拆成：

1. LLM 提出回查建议。
2. 后端把建议映射并聚合为可靠状态。
3. Orchestration 根据运行策略决定是否继续。

## 7. 未来三种接法（仅示意）

普通 Python 可以直接判断：

```python
result = evaluate_job_match(jd, candidate)
if result.needs_raw_review:
    requests = build_raw_review_requests(result)
    # 未来：交给 raw review 执行器
```

Tool Calling 可以把 `RawReviewRequest` 作为工具参数。模型或控制器选择是否调用工具，但工具只处理明确的 requirement 和搜索目标。

LangGraph 可以把 `needs_raw_review` 用作 conditional edge 的路由条件：`False` 进入结束节点，`True` 进入 raw-review 节点。本项目当前没有引入 LangGraph；这里只说明接口为什么已经能支持它。

## 8. 完整示例

假设结构化 Candidate 只写了“参与 AI 问答项目”，没有说明是否使用向量数据库。LLM 对“具备 RAG 项目经验”返回：

```python
LLMRequirementMatch(
    requirement_id="req_rag",
    status="insufficient_evidence",
    score=40,
    confidence="low",
    reason="结构化信息无法确认完整 RAG 链路",
    missing_information=["向量数据库", "召回与重排实现"],
    needs_raw_review=True,
    raw_review_reason="原始项目描述可能包含技术细节",
)
```

数据随后这样流动：

```text
结构化 Candidate
  ↓ LLM 语义判断
LLMRequirementMatch(needs_raw_review=True)
  ↓ Mapper 保留字段，并从 JD 补入名称、权重、must_have
RequirementMatchResult
  ↓ 后端聚合总分、硬条件、缺失信息和 review 状态
JobMatchResult(needs_raw_review=True, raw_review_requirement_ids=["req_rag"])
  ↓ build_raw_review_requests()
RawReviewRequest(
    requirement_id="req_rag",
    reason="原始项目描述可能包含技术细节",
    search_targets=["向量数据库", "召回与重排实现"],
)
  ↓ 未来 Orchestration 决定是否执行
未来 RawReview
```

注意：本次代码到 `RawReviewRequest` 为止。

## 9. 测试范围

本次执行了修改文件的 `python -m py_compile`，用于发现语法问题；还使用手工构造的 JD、Candidate 和 LLM DTO 做确定性 Service 冒烟检查，并使用项目已有 `scoring_integration_case.json` 中的 JD + Candidate 做了一次离线冒烟。当前默认 Python 环境没有安装项目声明的 `openai` 包，所以离线检查仅用一个最小替身绕过 `LLMClient` 的导入，不模拟 LLM 行为，也不改变被测评分逻辑。检查覆盖：

- raw-review 字段从 DTO 进入 Domain 后不丢失；
- LLM 顶层 raw-review 字段即使错误，也不会覆盖后端逐条聚合；
- 缺失信息按首次出现顺序去重；
- 专用回查原因空白时回退到普通 reason；
- 有回查时生成正确请求，无回查时返回空列表；
- 加权总分和 must-have `needs_confirmation` 仍按原规则计算；
- Pydantic 仍拒绝越界 score。

没有新增大量测试文件，也没有运行真实 DeepSeek 冒烟测试。真实集成测试需要可用的 API 配置和网络，会产生外部调用；这些都不是低风险 Mapper/聚合逻辑验证所必需。也没有为简单字段、Enum 或 getter 单独建立测试。

## 10. 复习速记

1. LLM 输出 DTO，不等于最终业务结果。
2. Mapper 负责 DTO 到 Domain 的可信转换。
3. JD 是名称、权重和 `must_have` 的权威来源。
4. LLM 负责语义判断，后端负责确定性计算。
5. 最终总分来自逐条分数乘归一化权重。
6. must-have 汇总由状态枚举确定，不使用模糊文本推断。
7. raw-review 顶层状态必须从逐条 Domain Result 聚合。
8. 辅助字段缺失优先容错，不应拖垮整份评分。
9. 核心 ID 和聚合一致性错误应尽早抛出。
10. `RawReviewRequest` 是评分与未来编排之间的连接点。
11. 是否真正回查由 Orchestration 决定。
12. 领域 Schema 保持框架无关，普通 Python、Tool Calling 和 LangGraph 都能复用。
