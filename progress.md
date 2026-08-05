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