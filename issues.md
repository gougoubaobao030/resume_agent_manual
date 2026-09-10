## ISSUE-001 PDF 文本重复清洗
类型：Enhancement

## ISSUE-002 Prompt Injection 防护
类型：Security / Enhancement

## ISSUE-003 批量简历解析
类型：Enhancement

## ISSUE-004 OCR / 扫描 PDF 支持
类型：Enhancement
当前决定：MVP 不支持，直接提示上传文本型 PDF

## ISSUE-005 LLM 输出异常的容错处理
类型：Tech Debt / Robustness

## ISSUE-006 为简历解析 API 增加 response_model

**类型：** Tech Debt / Enhancement  
**优先级：** P2  
**状态：** Backlog

### 现状
当前简历解析接口能够正常返回 Candidate 数据，
但 FastAPI 路由暂未显式声明 `response_model`。

### 潜在问题
目前接口返回结构主要依赖 service 层实际返回的数据，
API 层缺少明确的响应模型约束。

随着项目后续增加字段或修改内部实现，可能出现：
- 返回字段与预期 API 结构不一致
- 内部字段意外暴露给前端
- Swagger / OpenAPI 文档中的响应结构不够明确
- API 层缺少最终一次响应数据校验

### 后续优化
为简历解析接口定义专门的 Response Schema，例如：

`ResumeParseResponse`

并在 FastAPI 路由中声明：

`@router.post(..., response_model=ResumeParseResponse)`

由 API Schema 明确定义前端能够收到的数据结构。

### 当前决定
MVP 当前阶段暂不处理。

原因：
现有接口已经可以正常运行，
该修改属于接口契约和工程规范增强，
不影响当前简历解析主流程开发。

待核心流程跑通后统一进行 API 层规范化。

## ISSUE_007
* 真实 JD 解析测试中发现，LLM 容易受到“必须 / 优先 / 加分”等措辞影响，将 `must_have` 与 `weight` 自动关联，例如“必须”条件倾向获得较高权重。
* 当前处理：仅调整 Prompt，要求模型独立判断硬性条件与岗位重要度；最终权重仍允许由 HR 人工调整。
* 该问题影响有限，因为权重本身属于辅助建议，最终重要度应由实际招聘人员确认。


## ISSUE_008 非常重要（我想增加一个其他可能亮点字段）
## ISSUE_009 非常重要（为了有AI感需要自主反省决策）
## Issue_010：LLM 汇总字段与后端聚合职责

`LLMJobMatchResult` 中的 `overall_confidence`、`needs_raw_review`、`raw_review_requirement_ids`、`missing_information` 可暂时保留作为模型辅助输出。

最终业务状态仍以后端根据 `requirement_matches` 聚合结果为准，避免把可确定性计算的逻辑完全交给 LLM。

## issue_011:启动vue
cd D:\VSProject\Python\resume_agent_manual\frontend
npm run dev