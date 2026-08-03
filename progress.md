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

