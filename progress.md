# Resume Agent 开发进度记录

> 项目目标：开发一个 AI 简历筛选 Agent。
>
> 当前阶段重点：JD解析模块。
>
> 记录目的：方便后续聊天继续开发，不需要重新解释项目背景。

------------------------------------------------------------------------

# 一、项目基础信息

## 环境

Conda:

    resume_agent_py310

Python:

    3.10

## 技术栈

后端：

-   FastAPI
-   Uvicorn
-   Pydantic

LLM：

-   OpenAI兼容接口
-   当前使用 DeepSeek 模型

------------------------------------------------------------------------

# 二、项目结构

当前采用前后端分离：

    resume_agent/

    ├── backend/
    │
    │   ├── app/
    │   │   └── main.py
    │   │
    │   ├── api/
    │   ├── clients/
    │   ├── prompts/
    │   ├── schemas/
    │   ├── services/
    │   └── requirements.txt
    │
    ├── frontend/
    └── data/

注意：

`api`、`clients`、`prompts`、`schemas`、`services` 与 `app` 平级。

------------------------------------------------------------------------

# 三、已完成模块

## 1. FastAPI基础框架

完成：

-   FastAPI启动
-   VS Code Debug配置
-   后端端口固定18000

启动：

``` bash
uvicorn app.main:app --reload --port 18000
```

测试：

    GET /

返回：

``` json
{
    "message": "Resume Agent Backend Running"
}
```

------------------------------------------------------------------------

## 2. JD数据结构设计

文件：

    backend/schemas/jd.py

### JDInfo

完整岗位信息：

-   id
-   job_title
-   raw_text
-   requirements

### JDRequirement

单条岗位要求：

-   id
-   name
-   description
-   category
-   weight

category：

    technical
    experience
    education
    other

权重设计：

-   HR填写相对权重
-   不要求总和100
-   保存原始权重
-   评分阶段自动归一化

如果全部权重为0：

后续评分模块按等权处理。

------------------------------------------------------------------------

## 3. JD接口数据结构

新增：

### JDParseRequest

接收原始JD文本。

### JDParseResponse

返回：

-   JDInfo
-   warnings

### JDSaveRequest

用于HR修改后的正式保存。

设计原则：

解析和保存分离：

    输入JD
     ↓
    LLM解析
     ↓
    HR修改
     ↓
    正式保存

------------------------------------------------------------------------

# 四、LLM解析模块

## LLM专用结构

文件：

    prompts/jd_prompt.py
    services/jd_service.py

定义：

-   LLMJDRequirement
-   LLMJDResult

职责：

LLM负责：

-   岗位名称
-   要求名称
-   要求说明
-   category
-   建议权重

后端负责：

-   岗位ID
-   要求ID
-   原始JD文本

------------------------------------------------------------------------

## JD解析提示词

规则：

-   不虚构不存在的要求
-   合并重复要求
-   拆分不同能力
-   category限制
-   输出纯JSON

------------------------------------------------------------------------

# 五、LLM客户端

文件：

    backend/clients/llm_client.py

作用：

统一封装模型调用。

核心功能：

-   初始化客户端
-   读取配置
-   调用聊天接口
-   JSON解析
-   Markdown代码块清理
-   Pydantic校验

核心函数：

``` python
generate_structured(
    system_prompt,
    user_prompt,
    response_model
)
```

流程：

    Prompt
     ↓
    DeepSeek API
     ↓
    JSON
     ↓
    Pydantic校验
     ↓
    Python对象

------------------------------------------------------------------------

异常：

    LLMClientError
    LLMConfigError
    LLMRequestError
    LLMResponseError

------------------------------------------------------------------------

# 六、JD Service完整流程

当前流程：

    用户输入JD文本

    ↓

    parse_jd()

    ↓

    清理文本

    ↓

    生成Prompt

    ↓

    调用LLMClient

    ↓

    得到LLMJDResult

    ↓

    补充岗位ID

    ↓

    补充requirement ID

    ↓

    保存raw_text

    ↓

    转换JDInfo

    ↓

    返回JDParseResponse

目前：

DeepSeek真实解析已经成功。

------------------------------------------------------------------------

# 七、重要Bug与修改记录

## API Key认证失败

错误：

    401 Authentication Fails

原因：

之前使用：

    OPENAI_API_KEY
    OPENAI_BASE_URL
    OPENAI_MODEL

但实际调用DeepSeek。

Windows环境中存在旧OPENAI_API_KEY，导致读取错误Key。

解决：

改为通用命名：

    LLM_API_KEY
    LLM_BASE_URL
    LLM_MODEL
    LLM_TIMEOUT

代码：

``` python
os.getenv("LLM_API_KEY")
```

并：

``` python
load_dotenv(
    PROJECT_ROOT / ".env",
    override=True
)
```

确保项目配置优先。

------------------------------------------------------------------------

## Git

已完成阶段性git commit。

后续继续开发建议保持小步提交。

------------------------------------------------------------------------

# 八、当前验证状态

已确认：

✅ FastAPI启动

✅ Pydantic模型校验

✅ JD Prompt生成

✅ Mock LLM测试

✅ DeepSeek真实调用

✅ JDInfo生成

------------------------------------------------------------------------

# 九、下一步开发

## Step 1

创建：

    backend/api/jd.py

实现：

    POST /api/jd/parse

输入：

``` json
{
 "raw_text":"招聘信息..."
}
```

输出：

结构化JD。

------------------------------------------------------------------------

## Step 2

main.py注册JD路由。

## Step 3

Swagger测试真实接口。

## Step 4

实现HR调整：

-   新增要求
-   删除要求
-   修改要求
-   调整权重

------------------------------------------------------------------------

# 当前项目状态

已经完成：

    JD文本
     ↓
    Prompt
     ↓
    DeepSeek
     ↓
    结构化解析
     ↓
    Pydantic校验
     ↓
    JDInfo生成

下一阶段：

把内部Python函数封装成真正FastAPI接口。

## update: 2026年8月3日
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

## update 2026年8月4日
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

# update 2026年8月8日 开始简历上传与解析模块制作

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

## updata 2026年8月10日
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