# Resume Agent (RA)

[日本語](./README.md) | [English](./README_EN.md) | [简体中文](./README_CN.md)

Resume Agent（RA）是一套面向招聘场景的 AI 辅助简历筛选系统，用于帮助 HR 进行岗位信息整理、简历解析、候选人与岗位匹配评估，以及候选人能力发现。

当前系统主要由以下部分组成：

- FastAPI 后端
- Vue 3 前端
- SQLite 数据库
- Alembic 数据库迁移
- OpenAI-compatible LLM API
- PDF 简历解析与保存
- 中文 / 日文 / 英文多语言支持

## 1. 主要功能

当前 RA 提供以下主要功能：

- 用户登录与 Session 认证
- JD 创建与 AI 解析
- PDF 简历上传与结构化解析
- 候选人管理
- 候选人与岗位匹配评分
- Talent Discovery
- AI 自动能力发现
- HR 指定能力分析
- 查看原始简历
- 多语言支持
  - 简体中文
  - 日文
  - 英文

## 2. 运行环境

### Python

推荐：

```text
Python 3.10
```

当前实际开发与验证环境：

```text
Python 3.10.20
```

RA 当前实际开发环境使用 Conda。

Conda 并非代码层面的强制要求，但为了尽量复现当前开发环境，推荐使用 Conda。

### Node.js

建议使用：

```text
Node.js 22.12.0 或以上
```

根据当前 `package-lock.json` 中的依赖要求，推荐 Node.js 22.12.0 或以上版本。

### 操作系统

项目目前主要在 Windows 环境中开发和验证。

本文命令以 Windows PowerShell 为例。

## 3. 项目结构

```text
resume_agent_manual/
├─ backend/                 FastAPI 后端
│  ├─ api/                  API 路由
│  ├─ app/                  FastAPI 应用入口
│  ├─ clients/              LLM 等外部服务客户端
│  ├─ repositories/         数据访问层
│  ├─ services/             业务逻辑
│  ├─ scripts/              管理脚本
│  ├─ tests/                后端测试
│  ├─ alembic/              数据库迁移
│  ├─ requirements.txt      Python 依赖
│  └─ alembic.ini
│
├─ frontend/                Vue 前端
│  ├─ src/
│  ├─ package.json
│  └─ package-lock.json
│
├─ data/                    运行时数据
│  ├─ avatars/
│  └─ resumes/
│
├─ docs/                    项目文档
├─ .env.example             环境变量模板
└─ README.md
```

## 4. 首次安装

### 第一步：获取源码

```powershell
git clone <repository-url>
cd resume_agent_manual
```

### 推荐：Windows 自动初始化

在 Windows 上 fresh clone 后，推荐双击项目根目录中的 `setup_windows.bat`，也可以在终端执行：

```powershell
.\setup_windows.bat
```

该脚本会自动检查 Conda，创建或使用 `resume_agent_py310` 环境，安装 Python 后端依赖，在 `.env` 不存在时从 `.env.example` 创建 `.env`，执行 Alembic 数据库迁移，检查 Node.js，并安装前端依赖。

setup 完成后，以下步骤仍需人工完成：

- 如果使用真实 LLM，需要编辑项目根目录中的 `.env`，为 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 填写有效配置。
- 创建首个用户。密码由脚本交互输入，不应写入命令或 README。

```powershell
cd backend
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

初始化完成后，日常启动时可以双击项目根目录中的 `start_ra.bat`，也可以执行：

```powershell
.\start_ra.bat
```

该脚本会激活 `resume_agent_py310`，分别在独立且保持打开的终端窗口中启动 FastAPI 后端和 Vue 前端，并打开浏览器访问 `http://127.0.0.1:12140/login`。

自动脚本只是对下方原有手动命令的封装。如果 `setup_windows.bat` 或 `start_ra.bat` 执行失败，仍然可以按照下方手动步骤继续安装或启动。

## 5. 后端环境配置

### 第二步：创建 Python 环境

推荐使用 Conda：

```powershell
conda create -n resume_agent_py310 python=3.10
conda activate resume_agent_py310
```

确认 Python 版本：

```powershell
python --version
```

预期：

```text
Python 3.10.x
```

### 第三步：安装后端依赖

在项目根目录执行：

```powershell
python -m pip install -r .\backend\requirements.txt
```

## 6. 配置环境变量

复制 `.env.example`：

```powershell
Copy-Item .\.env.example .\.env
```

之后编辑 `.env`。

典型配置：

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=
LLM_TIMEOUT=60

JD_USE_MOCK=false
RESUME_USE_MOCK=false
SCORING_USE_MOCK=false
TALENT_USE_MOCK=false
TRANSLATION_USE_MOCK=false

DATABASE_URL=sqlite+pysqlite:///./data/resume_agent.db
COOKIE_SECURE=false
```

不要将真实 API Key 提交到 Git。

### LLM 配置说明

RA 使用 OpenAI Python SDK，并通过 OpenAI-compatible API 调用模型。

真实 AI 模式下主要需要：

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

以下模块会使用 LLM：

- JD 解析
- 简历解析
- 岗位匹配评分
- Talent Discovery
- 翻译

如果对应模块的 `*_USE_MOCK` 设置为 `true`，则该模块可以使用 mock 数据。

默认情况下 mock 模式关闭。

如果没有配置有效 LLM，后端本身仍可以启动，但在执行 AI 相关功能时会报模型配置错误。

## 7. 初始化数据库

进入后端目录：

```powershell
cd backend
```

执行 Alembic：

```powershell
python -m alembic upgrade head
```

系统会创建 SQLite 数据库以及所需数据表。

默认数据库文件：

```text
data/resume_agent.db
```

SQLite 数据库文件不需要提交至 Git。

## 8. 创建首个用户

RA 不提供默认用户名和密码。

数据库初始化后，需要手动创建第一个用户。

```powershell
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

脚本会要求交互式输入两次密码。

密码要求：

```text
至少 8 位
```

完整格式：

```powershell
python .\scripts\manage_user.py create USERNAME [--display-name NAME] [--language zh-CN|ja-JP|en-US]
```

示例：

```powershell
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

`--display-name` 可选。

`--language` 可选，默认：

```text
zh-CN
```

## 9. 启动后端

保持位于 `backend` 目录：

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18000
```

后端地址：

```text
http://127.0.0.1:18000
```

FastAPI API 文档：

```text
http://127.0.0.1:18000/docs
```

## 10. 前端环境配置

打开新的 PowerShell。

从项目根目录进入：

```powershell
cd frontend
```

安装前端依赖：

```powershell
npm ci
```

由于项目已经包含 `package-lock.json`，fresh clone 后推荐使用 `npm ci`。

启动 Vue 前端：

```powershell
npm run dev
```

前端地址：

```text
http://127.0.0.1:12140
```

登录页面：

```text
http://127.0.0.1:12140/login
```

## 11. 本地开发结构

```text
Browser
   │
   ▼
Vue / Vite
127.0.0.1:12140
   │
   │ /api
   ▼
Vite Proxy
   │
   ▼
FastAPI
127.0.0.1:18000
   │
   ├─ SQLite
   ├─ Resume Storage
   └─ LLM API
```

前端 API 请求统一使用 `/api/...` 相对路径。

Vite 会代理至：

```text
http://127.0.0.1:18000
```

因此默认本地开发模式下不需要额外配置 CORS。

## 12. Cookie 配置

本地 HTTP 环境应设置：

```env
COOKIE_SECURE=false
```

如果本地 HTTP 环境错误设置：

```env
COOKIE_SECURE=true
```

可能出现：

1. 登录接口返回成功；
2. 浏览器不保存或不发送 Secure Cookie；
3. 后续 `/api/auth/me` 等接口返回 `401 Unauthorized`；
4. 页面表现为登录后仍未登录，或者刷新后退出。

正式 HTTPS 环境通常应设置：

```env
COOKIE_SECURE=true
```

## 13. 简历上传与保存

当前 RA 支持 PDF 简历。

上传后的原始 PDF 保存于：

```text
data/resumes/<candidate_id>/original.pdf
```

数据库中保存的是相对路径，而不是开发电脑的绝对路径。

因此源码在不同电脑间具有较好的可移植性。

上传后的简历文件不会提交至 Git。

## 14. 运行时文件

以下内容通常不应提交到 Git：

```text
.env
data/resume_agent.db
data/*.db-wal
data/*.db-shm
data/resumes/
frontend/node_modules/
Python __pycache__/
```

以下内容应随源码一起提交：

```text
.env.example
backend/requirements.txt
backend/alembic/
backend/alembic.ini
frontend/package.json
frontend/package-lock.json
```

## 15. 首次运行验证

环境安装完成后，建议按照以下流程验证：

1. 启动 FastAPI 后端
2. 启动 Vue 前端
3. 打开 `http://127.0.0.1:12140/login`
4. 使用 `manage_user.py` 创建的用户登录
5. 创建或解析 JD
6. 上传 PDF 简历
7. 执行简历解析
8. 执行岗位匹配评分
9. 执行 Talent Discovery
10. 在候选人页面查看分析结果

如果使用真实 LLM，AI 相关流程需要有效的 LLM 配置。

## 16. 常见问题

### 登录成功后出现 401

本地 HTTP 环境检查：

```env
COOKIE_SECURE=false
```

### AI 功能提示模型配置错误

检查：

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

### 前端无法启动

检查 Node.js：

```powershell
node --version
```

建议使用 Node.js 22.12.0 或以上。

之后重新执行：

```powershell
npm ci
```

### 数据库未初始化

执行：

```powershell
cd backend
python -m alembic upgrade head
```

### 没有可登录用户

执行：

```powershell
cd backend
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

## 17. 当前项目范围

当前 RA 主要用于本地环境、内部使用以及项目验证。

当前仓库提供：

- Vue / Vite 前端
- FastAPI 后端
- SQLite 数据库
- LLM API 集成

当前不包含以下生产环境基础设施：

- 生产级反向代理
- HTTPS 终止配置
- Docker / Kubernetes
- 生产环境前端静态托管
- 云基础设施部署
