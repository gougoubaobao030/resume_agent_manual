# Resume Agent 开发进度


## 第一模块：JD解析模块


### 已完成

- 创建 Conda 环境
  - 环境名:
    resume_agent_py310
  - Python版本:
    3.10


- 创建项目基础目录

- 完成后端基础架构

技术:
- FastAPI
- Uvicorn
- Pydantic


当前目录:

resume_agent/
├── backend
├── frontend
├── data

## 项目目录约定

后端采用平行目录结构。

`api`、`clients`、`prompts`、`schemas`、`services`
均直接位于 `backend` 目录下，并与 `app` 文件夹平级。

`app` 文件夹当前用于存放 FastAPI 启动入口：

```text
backend/app/main.py

backend/
├── app/
│   └── main.py
├── api/
├── clients/
├── prompts/
├── schemas/
├── services/
├── ....
└── requirements.txt


- FastAPI启动成功

启动命令:

uvicorn app.main:app --reload -port 18000


测试:

GET /

返回:

{
 "message":"Resume Agent Backend Running"
}


再补上启动配置：

```markdown
## 后端启动配置

后端已配置 VS Code 调试启动。

调试配置名称：

```text
Backend FastAPI


### 当前状态

完成:
- 后端基础框架

未完成:
- JD数据结构设计
- JD解析接口
- LLM调用
- HR权重调整功能
- 前端页面


### 下一步

开发JD解析模块:
1. 设计JD Pydantic模型
2. 编写JD API
3. 接入LLM解析
4. 实现HR修改权重

## JD解析模块

### 已完成：JD数据结构设计

已创建：

- `backend/schemas/jd.py`
- 各后端目录的 `__init__.py`
- `backend/test_jd_schema.py`

JD数据结构包括：

#### JDInfo

- `id`：岗位唯一标识，自动生成
- `job_title`：岗位名称
- `raw_text`：原始JD文本
- `requirements`：结构化岗位要求列表

#### JDRequirement

- `id`：条目唯一标识，自动生成
- `name`：要求名称
- `description`：详细要求
- `category`：要求分类
- `weight`：HR设置的相对权重

分类目前限定为：

- `technical`
- `experience`
- `education`
- `other`

权重设计：

- HR填写相对权重
- 权重总和不要求为100
- 数据中保存HR填写的原始权重
- 实际评分时再自动归一化
- 所有权重均为0时，后续评分模块按等权处理

验证情况：

- JD对象可以正常创建并输出JSON
- 非法分类会被Pydantic拦截
- 负数权重会被Pydantic拦截

### 下一步

设计并实现JD解析接口的请求与响应结构，然后编写LLM提示词。

### 已完成：JD接口数据结构设计

已在 `backend/schemas/jd.py` 中增加：

- `JDParseRequest`
  - 用于提交原始JD文本
  - 当前只包含 `raw_text`
  - 限制文本长度为10至20000字符

- `JDParseResponse`
  - 返回结构化 `JDInfo`
  - 支持返回非致命提示 `warnings`

- `JDSaveRequest`
  - 用于HR修改、增删条目、调整权重后提交最终JD
  - 正式保存时要求至少包含一条岗位要求

接口设计原则：

- JD解析和正式保存分开
- 解析接口不直接代表数据已保存
- HR可以在前端修改完整要求列表后一次提交
- 解析结果允许要求列表为空，并通过warnings提示
- 正式保存时岗位要求列表不能为空
- 新建和修改JD可以复用 `JDSaveRequest`
- 岗位ID由接口路径或后端管理，不在保存请求中重复提交

下一步：

- 设计JD解析提示词
- 让LLM只输出岗位名称和要求列表
- 后端补充岗位ID、条目ID和原始JD文本

### 已完成：JD解析提示词与模型输出结构

已创建：

- `backend/prompts/jd_prompt.py`
- `backend/services/jd_service.py`
- `backend/test_jd_prompt.py`
- `backend/test_jd_service.py`

已增加模型专用数据结构：

- `LLMJDRequirement`
- `LLMJDResult`

职责划分：

- LLM只负责返回：
  - 岗位名称
  - 要求名称
  - 要求说明
  - 要求分类
  - 建议相对权重

- LLM不负责返回：
  - 岗位ID
  - 要求条目ID
  - 原始JD文本

- 后端负责：
  - 自动生成岗位ID
  - 自动生成要求条目ID
  - 保存原始JD文本
  - 将模型结果转换为正式的 `JDInfo`

提示词规则包括：

- 不虚构原文中没有的岗位要求
- 合并含义高度重复的要求
- 拆分含义明显不同的要求
- category只能使用：
  - technical
  - experience
  - education
  - other
- 建议权重为相对权重，不要求总和为100
- 核心要求权重较高
- 优先项和加分项通常使用较低权重
- 模型只输出结构化JSON，不输出额外解释

当前验证：

- 提示词可以正常生成
- 模型模拟结果可以通过Pydantic校验
- 后端可以补充岗位ID、条目ID和原始JD文本
- 可以成功生成完整 `JDInfo`

下一步：

- 实现统一的LLM客户端
- 配置模型API Key、Base URL和模型名
- 调用真实模型并解析为 `LLMJDResult`

**测试正式大模型**
发现401错误
已经git 并commit
交给codex查找bug，目前推测大概是setx变量问题

### 已完成：统一LLM客户端与真实JD解析

已创建：

- `backend/clients/llm_client.py`
- `backend/test_llm_config.py`
- `backend/test_jd_service_mock.py`
- `backend/test_jd_service_real.py`
- 项目根目录 `.env.example`

模型配置：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `LLM_TIMEOUT`

真实密钥保存在项目根目录 `.env` 中：

- `.env` 已加入 `.gitignore`
- 不在进度报告中记录真实API密钥

LLM客户端职责：

- 统一初始化OpenAI兼容客户端
- 统一读取模型配置
- 统一调用聊天补全接口
- 要求模型返回JSON
- 清理Markdown JSON代码块
- 将JSON校验为指定的Pydantic模型
- 统一处理配置错误、连接错误、超时、API错误和响应格式错误

已定义异常：

- `LLMClientError`
- `LLMConfigError`
- `LLMRequestError`
- `LLMResponseError`

JD服务已实现真实解析流程：

1. 清理原始JD文本
2. 构建系统提示词和用户提示词
3. 调用统一LLM客户端
4. 将结果校验为 `LLMJDResult`
5. 后端自动补充岗位ID
6. 后端自动补充要求条目ID
7. 后端保留原始JD文本
8. 转换为正式 `JDInfo`
9. 生成非致命解析警告
10. 返回 `JDParseResponse`

测试情况：

- 模型配置读取成功
- Mock模型调用测试成功
- 真实模型JD解析测试成功
- 模型结果可通过Pydantic校验
- 后端可以生成完整JD解析结果

下一步：

- 创建 `backend/api/jd.py`
- 实现 `POST /api/jd/parse`
- 在 `backend/app/main.py` 注册JD路由
- 通过FastAPI Swagger文档测试真实接口

## LLM 配置管理优化（2026-08-03）

### 背景

初期项目使用 OpenAI 兼容接口调用 DeepSeek API，但环境变量名称沿用了：

* `OPENAI_API_KEY`
* `OPENAI_BASE_URL`
* `OPENAI_MODEL`

由于实际调用对象并不限定为 OpenAI，且开发环境中曾设置过 Windows 全局环境变量 `OPENAI_API_KEY`，导致项目运行时可能读取错误的 API Key，引发模型服务认证失败。

### 问题现象

调用 JD 解析接口时：

```text
JD解析失败：模型服务返回错误，状态码：401
```

进一步增强 `APIStatusError` 诊断信息后确认：

```text
Authentication Fails, Your api key is invalid
```

最终定位为：

* 项目读取到了无效的 API Key；
* 环境变量名称与实际模型服务不匹配；
* 系统环境变量与项目配置存在潜在冲突。

### 解决方案

将 LLM 相关环境变量统一改为通用命名：

修改前：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
```

修改后：

```env
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
LLM_TIMEOUT=
```

同时修改：

`backend/clients/llm_client.py`

配置读取逻辑：

```python
self.api_key = os.getenv("LLM_API_KEY", "").strip()
self.base_url = os.getenv("LLM_BASE_URL", "").strip()
self.model = os.getenv("LLM_MODEL", "").strip()
```

并保留：

```python
load_dotenv(
    PROJECT_ROOT / ".env",
    override=True,
)
```

确保项目 `.env` 配置优先于系统遗留环境变量。

### 验证结果

修改完成后：

* JD解析接口调用成功；
* DeepSeek API认证通过；
* LLM客户端调用链正常运行。

### 经验总结

LLM服务配置不应绑定具体厂商名称，应使用通用配置：

```
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

这样未来切换不同兼容 OpenAI API 的模型服务时，无需修改业务代码。

### 已完成：JD解析HTTP接口

新增：

- `backend/api/jd.py`

实现接口：

POST `/api/jd/parse`

请求：

- JDParseRequest
- 接收原始JD文本


响应：

- JDParseResponse
- 返回结构化JD


FastAPI路由：

- 已在 `app/main.py` 注册


异常处理：

不同错误转换为不同HTTP状态码：

- LLMConfigError
  - 500
  - 模型配置错误

- LLMRequestError
  - 503
  - 模型服务请求失败

- LLMResponseError
  - 502
  - 模型返回格式错误

- ValueError
  - 400
  - 用户输入错误


测试：

- FastAPI启动成功
- Swagger文档出现 `/api/jd/parse`
- 可以通过接口调用真实LLM完成JD解析


当前JD模块流程：

用户输入JD
↓
FastAPI接口
↓
jd_service
↓
LLMClient
↓
LLM解析
↓
Pydantic校验
↓
生成JDInfo
↓
返回JSON


下一步：

开发HR端JD管理功能：

- 查看解析结果
- 修改要求条目
- 增加要求
- 删除要求
- 调整权重
- 保存最终JD

## 已完成：JD保存与修改管理接口

新增：

- services/jd_repository.py

实现临时JD存储层：

- save_jd()
- get_jd()
- update_jd()

当前使用内存dict模拟数据库，
后续可替换为SQLite。


新增接口：

POST /api/jd

功能：
- 保存HR确认后的JD
- 生成正式JD数据


GET /api/jd/{job_id}

功能：
- 根据岗位ID获取JD


PUT /api/jd/{job_id}

功能：
- 修改岗位名称
- 修改要求条目
- 修改权重


设计原则：

- AI解析结果不是最终数据
- HR拥有最终确认权
- 保存的是HR确认后的JD
- 原始JD文本保持不变
- 权重保存原始值，评分阶段自动归一化


当前JD模块完整流程：

输入JD
↓
LLM解析
↓
HR确认修改
↓
保存岗位要求
↓
后续评分模块读取


下一步：

开发简历解析模块：
- PDF上传
- Unstructured解析
- 简历结构化Schema
- 候选人信息提取

# 2026年8月8日 开始简历上传与解析模块的制作
# update 2026年8月8日

## 已完成：简历结构化数据模型设计（Candidate Schema）


新增：

backend/schemas/resume.py


设计目标：

Candidate作为系统内部保存的候选人标准数据结构。

用于后续：

- JD匹配评分
- 证据潜力评分
- 开放发现评分
- 候选人详情展示



Candidate结构：

Candidate

├ basic_info

├ education

├ work_experience

├ projects

├ skills

├ languages

├ achievements

├ certifications


├ candidate_evidence ⭐

├ custom_attributes


├ raw_text ⭐

└ extraction_metadata



字段设计说明：


1. 基础结构化字段

用于保存传统简历信息：

- 教育经历
- 工作经历
- 项目经历
- 技能
- 语言
- 荣誉
- 证书



2. candidate_evidence（重点设计）


用途：

保存除了标准字段之外，
但可能影响人才评价的事实信息。


例如：

- 自主学习经历
- 开源贡献
- 创业经历
- 特殊培养经历
- 社群活动
- 多语言经历
- 研究经历


设计原则：

只保存事实，不进行价值评价。

例如：

正确：

"候选人自主学习Python并完成RAG项目"


错误：

"候选人学习能力强"


因为后续潜力评分阶段再进行分析。



3. custom_attributes


用途：

预留未来扩展字段。


例如：

- 日本企业特殊关注信息
- 签证状态
- 希望工作地点


不影响当前MVP。



4. raw_text


保存PDF提取后的原始简历文本。


原因：

结构化解析可能丢失上下文。

后续评分和潜力分析可以结合原始文本。



5. extraction_metadata


保存解析过程信息：

例如：

- 使用解析工具
- 使用模型
- 来源文件
- confidence


用于后续调试和系统优化。


---

设计原则：

Candidate是系统最终保存的数据。

不是直接让LLM生成。

后续采用：

PDF文本

↓

ResumeLLMResult

↓

后端补充ID/raw_text/metadata

↓

Candidate

## update 2026年8月10日
## 已完成：ResumeLLMResult设计


新增：

ResumeLLMResult


设计原则：

LLM输出模型与系统内部Candidate模型分离。


原因：

- LLM负责信息抽取
- Candidate负责业务保存


避免：

- LLM生成系统字段
- 数据结构互相污染
- 后续字段调整困难



新增LLM专用Schema：

- LLMBasicInfo
- LLMEducation
- LLMWorkExperience
- LLMProject
- LLMCandidateEvidence
- ResumeLLMResult



数据流：

PDF文本

↓

DeepSeek

↓

ResumeLLMResult

↓

后端转换

↓

Candidate



设计思想：

采用分层设计：

输入层
↓
LLM解析层
↓
业务数据层
↓
评分层



candidate_evidence：

由LLM负责提取。

原则：

只提取简历明确表达的事实。

不进行能力评价。

评价将在后续潜力评分模块完成。

## update 2026年8月11日
## 已完成：简历解析 Prompt 设计


新增：

backend/prompts/resume_prompt.py


作用：

定义简历结构化解析规则。



设计：

System Prompt:

定义模型角色和抽取原则。


User Prompt:

传入具体简历文本。



核心规则：

- 只提取简历明确事实
- 不编造信息
- 不评价候选人
- 不进行岗位匹配



字段抽取：

- basic_info
- education
- work_experience
- projects
- skills
- languages
- achievements
- certifications


重点：

candidate_evidence


用于保存：

标准字段之外，
可能影响人才评价的事实信息。


例如：

- 开源贡献
- 自主学习经历
- 特殊培养经历
- 创业经历
- 跨领域经历


原则：

只记录事实。

不输出：

"学习能力强"

而输出：

"自主学习Python并完成项目"



设计思想：

Prompt按业务拆分。

遵循单一职责原则。

后续支持Prompt版本管理。

## update 2026年8月15日
## 已完成：PDF文本解析模块


新增：

backend/services/pdf_service.py


技术：

unstructured[pdf]


作用：

将上传的PDF简历转换为纯文本。



流程：

PDF文件

↓

unstructured.partition_pdf()

↓

Document Elements

↓

文本拼接

↓

raw_text



设计原则：

pdf_service只负责文档解析。

不负责：

- LLM调用
- 简历字段提取
- 候选人评分



异常策略：

MVP阶段：

只支持文本型PDF。

解析失败：

提示：

"无法解析，请上传文本型PDF"



设计思想：

遵循单一职责原则。

PDF解析层与简历业务解析层分离。

## update 2026年8月16日

## 已完成：Resume Service 核心业务流程

新增：

backend/services/resume_service.py


### 核心职责

Resume Service作为简历解析业务编排层，
负责组合：

- PDF文本提取
- Resume Prompt
- LLM Client
- ResumeLLMResult
- Candidate


### 核心函数

#### parse_resume_text()

输入：

简历原始文本

流程：

raw_text
↓
清理文本
↓
构建Resume Prompt
↓
DeepSeek
↓
ResumeLLMResult
↓
转换Candidate


#### parse_resume_pdf()

输入：

PDF路径

流程：

PDF
↓
pdf_service.extract_pdf_text()
↓
raw_text
↓
parse_resume_text()
↓
Candidate


#### _build_candidate()

负责：

ResumeLLMResult
↓
Candidate


转换内容：

- LLMBasicInfo → BasicInfo
- LLMEducation → Education
- LLMWorkExperience → WorkExperience
- LLMProject → Project
- LLMCandidateEvidence → CandidateEvidence


后端补充：

- candidate_id
- raw_text
- custom_attributes
- extraction_metadata


### 设计思想

1. Service / Orchestration

resume_service只负责业务编排，
具体PDF解析由pdf_service完成，
模型调用由llm_client完成。


2. DTO与领域模型分离

ResumeLLMResult：

LLM输出DTO

Candidate：

系统内部业务模型


3. Mapper / Assembler

通过_build_candidate()隔离：

LLM数据结构

和

系统业务结构


4. Separation of Concerns

parse_resume_text和parse_resume_pdf分离，
便于分别测试LLM解析和PDF解析。


当前简历核心数据流：

PDF
↓
Unstructured
↓
raw_text
↓
Resume Prompt
↓
DeepSeek
↓
ResumeLLMResult
↓
Mapper
↓
Candidate

## update 2026年8月17日
## 已完成：parse_resume_text 真实 DeepSeek 测试
真实复杂简历 → DeepSeek → ResumeLLMResult 结构化抽取跑通

验证流程：

手工简历文本
↓
Resume Prompt
↓
DeepSeek
↓
ResumeLLMResult
↓
_build_candidate()
↓
Candidate

验证内容：

- DeepSeek真实调用成功
- ResumeLLMResult通过Pydantic校验
- Candidate转换成功
- 系统字段由后端补充
- candidate_evidence可以保留标准字段之外的重要事实
- 未接入PDF，当前仅验证text → Candidate核心链路

## update 2026年8月17日
## 已完成：单份简历解析 FastAPI 接口

新增：

backend/api/resume.py


接口：

POST /api/resume/parse


输入：

单份 PDF 简历。


处理流程：

UploadFile
↓
校验 PDF
↓
保存临时文件
↓
parse_resume_pdf()
↓
Unstructured提取文本
↓
DeepSeek结构化解析
↓
ResumeLLMResult
↓
Candidate
↓
返回JSON
↓
删除临时文件


接口响应：

Candidate


异常处理：

- 非PDF文件：400
- 无法解析文本型PDF：400
- LLM配置错误：500
- LLM请求失败：503
- LLM返回格式错误：502


临时文件策略：

当前MVP不永久保存原始PDF。

上传文件只用于本次解析：

上传
↓
临时保存
↓
解析
↓
删除


source_file：

Candidate记录用户上传的真实文件名，
而不是服务器临时文件名。


设计思想：

API层只负责HTTP输入输出和文件适配。

Resume Service负责业务流程。

通过临时文件将FastAPI UploadFile适配为
parse_resume_pdf()需要的文件路径。


当前单份简历完整链路：

PDF Upload
↓
FastAPI
↓
Temporary File
↓
Unstructured
↓
DeepSeek
↓
ResumeLLMResult
↓
Candidate
↓
HTTP Response

## update 2026年9月6日
## 已完成：批量简历解析后端

支持：

单次上传1-30份PDF简历。
MVP实际目标场景为10-30份。


新增Schema：

- ResumeParseItemResult
- ResumeBatchParseResponse


单份结果包含：

- filename
- success
- candidate
- error


批量结果包含：

- total
- success_count
- failed_count
- results


新增Service：

parse_resume_batch()


设计：

批量解析复用已有parse_resume_pdf()。

每份简历独立try/except：

某份解析失败不会中断其他简历。


新增API：

POST /api/resume/parse-batch


处理流程：

多个UploadFile
↓
PDF格式检查
↓
分别保存临时文件
↓
parse_resume_batch()
↓
逐份parse_resume_pdf()
↓
Candidate / Error
↓
ResumeBatchParseResponse
↓
统一删除临时文件


失败策略：

非PDF：
属于请求格式错误，整个请求返回400。

合法PDF但无法解析：
只标记该份失败，
继续处理其他简历。


当前暂时串行调用LLM。

原因：

优先保证正确性和稳定性，
后续性能优化再增加有限并发。


设计思想：

- 单份能力作为批量处理原子操作
- Result Object
- Fault Isolation（故障隔离）
- 批量任务局部失败
- 后续可扩展Bounded Concurrency