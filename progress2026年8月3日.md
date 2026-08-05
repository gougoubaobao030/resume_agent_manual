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