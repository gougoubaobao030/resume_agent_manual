# Resume Agent (RA)

[日本語](./README.md) | [English](./README_EN.md) | [简体中文](./README_CN.md)

Resume Agent (RA) is an AI-assisted resume screening application designed to support recruiters in processing job descriptions, analyzing resumes, evaluating candidate-job fit, and discovering candidate capabilities.

The current application consists of:

- FastAPI backend
- Vue 3 frontend
- SQLite database
- Alembic database migrations
- OpenAI-compatible LLM API integration
- PDF resume parsing and storage
- Multilingual UI and analysis support

## 1. Main Features

RA currently provides the following main functions:

- User login and session authentication
- Job Description (JD) creation and AI parsing
- Resume PDF upload and structured parsing
- Candidate management
- Candidate-job matching and scoring
- Talent Discovery
- AI-discovered capability analysis
- HR-specified capability analysis
- Original resume viewing
- Multilingual support:
  - Simplified Chinese
  - Japanese
  - English

## 2. System Requirements

### Python

Recommended:

```text
Python 3.10
```

The development and verified runtime environment currently uses:

```text
Python 3.10.20
```

Conda is recommended for reproducing the development environment, although it is not technically required.

### Node.js

Use:

```text
Node.js 22.12.0 or later
```

The current frontend dependency lock file requires Node.js 22.12.0 or later.

### Supported OS

The project is primarily developed and verified on Windows.

The commands in this README use Windows PowerShell.

## 3. Project Structure

```text
resume_agent_manual/
├─ backend/                 FastAPI backend
│  ├─ api/                  API routes
│  ├─ app/                  FastAPI application entry point
│  ├─ clients/              External service / LLM clients
│  ├─ repositories/         Database access layer
│  ├─ services/             Business logic
│  ├─ scripts/              Management scripts
│  ├─ tests/                Backend tests
│  ├─ alembic/              Database migrations
│  ├─ requirements.txt      Python dependencies
│  └─ alembic.ini
│
├─ frontend/                Vue frontend
│  ├─ src/
│  ├─ package.json
│  └─ package-lock.json
│
├─ data/                    Runtime data
│  ├─ avatars/
│  └─ resumes/              Created automatically when resumes are uploaded
│
├─ docs/                    Project documentation
├─ .env.example             Environment variable template
└─ README.md
```

## 4. Initial Setup

### Step 1: Clone the repository

```powershell
git clone <repository-url>
cd resume_agent_manual
```

### Recommended: automated Windows setup

After a fresh clone on Windows, the recommended approach is to double-click `setup_windows.bat` in the project root or run it from a terminal:

```powershell
.\setup_windows.bat
```

The script checks for Conda, creates or reuses the `resume_agent_py310` environment, installs the Python backend dependencies, creates `.env` from `.env.example` when `.env` does not exist, runs the Alembic database migrations, checks Node.js, and installs the frontend dependencies.

The following steps still require manual action after setup:

- For real LLM usage, edit `.env` in the project root and provide valid values for `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`.
- Create the first user. The password is entered interactively and must not be written into the command or README.

```powershell
cd backend
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

For normal daily startup after initialization, double-click `start_ra.bat` in the project root or run:

```powershell
.\start_ra.bat
```

The script activates `resume_agent_py310`, starts the FastAPI backend and Vue frontend in separate terminal windows that remain open, and opens `http://127.0.0.1:12140/login` in the browser.

These automation scripts are wrappers around the existing manual commands documented below. If `setup_windows.bat` or `start_ra.bat` fails, you can continue the installation or startup by following the manual steps below.

## 5. Backend Setup

### Step 2: Create the Python environment

Recommended Conda setup:

```powershell
conda create -n resume_agent_py310 python=3.10
conda activate resume_agent_py310
```

Confirm the Python version:

```powershell
python --version
```

Expected:

```text
Python 3.10.x
```

### Step 3: Install backend dependencies

From the project root:

```powershell
python -m pip install -r .\backend\requirements.txt
```

### Step 4: Create the environment configuration

Copy the environment template:

```powershell
Copy-Item .\.env.example .\.env
```

Then edit `.env` and configure the required LLM settings.

Typical configuration:

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

Do not commit the real `.env` file or API keys to Git.

### LLM configuration

RA uses the OpenAI Python SDK with an OpenAI-compatible API.

For real AI processing, the following values must be correctly configured:

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

The following modules use the LLM:

- JD parsing
- Resume parsing
- Candidate-job scoring
- Talent Discovery
- Translation

If a module's corresponding `*_USE_MOCK` setting is set to `true`, that module can use mock data instead of the real LLM.

By default, mock mode is disabled.

Without valid LLM configuration, the backend itself can still start, but AI-related operations will fail when invoked.

## 6. Initialize the Database

Change to the backend directory:

```powershell
cd backend
```

Run all Alembic migrations:

```powershell
python -m alembic upgrade head
```

This creates the SQLite database and all required database tables.

The default database file is:

```text
data/resume_agent.db
```

The SQLite database file does not need to be included in the source repository.

## 7. Create the First User

RA does not include a default username or password.

After initializing the database, create the first user:

```powershell
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

The command will ask for the password interactively.

Password requirements:

```text
Minimum 8 characters
```

General command format:

```powershell
python .\scripts\manage_user.py create USERNAME [--display-name NAME] [--language zh-CN|ja-JP|en-US]
```

Example:

```powershell
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

The `--display-name` option is optional.

The `--language` option is optional and defaults to:

```text
zh-CN
```

## 8. Start the Backend

Remain in the `backend` directory and run:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18000
```

The backend will be available at:

```text
http://127.0.0.1:18000
```

FastAPI API documentation is available at:

```text
http://127.0.0.1:18000/docs
```

## 9. Frontend Setup

Open another PowerShell window.

From the project root:

```powershell
cd frontend
```

Install frontend dependencies:

```powershell
npm ci
```

`npm ci` is recommended because the project includes `package-lock.json`.

Then start the Vue development server:

```powershell
npm run dev
```

The frontend will be available at:

```text
http://127.0.0.1:12140
```

Login page:

```text
http://127.0.0.1:12140/login
```

## 10. Local Development Architecture

During local development:

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

Frontend API requests use relative `/api/...` URLs.

Vite proxies these requests to:

```text
http://127.0.0.1:18000
```

Therefore, the default local development configuration does not require additional CORS configuration.

## 11. Cookie Configuration

For local HTTP development, use:

```env
COOKIE_SECURE=false
```

Do not set this to `true` when running the application locally over ordinary HTTP.

If `COOKIE_SECURE=true` is used with local HTTP, login may appear successful but the browser may not send the authentication cookie on subsequent requests, resulting in `401 Unauthorized`.

For an HTTPS production deployment, `COOKIE_SECURE=true` should normally be used.

## 12. Resume Upload and Storage

The current application supports PDF resumes.

Uploaded original resumes are stored under:

```text
data/resumes/<candidate_id>/original.pdf
```

The database stores a relative resume path rather than an absolute local computer path.

This allows the project to remain portable between machines.

Runtime resume files are not committed to Git.

## 13. Database and Runtime Data

The following files are generated at runtime and should not normally be committed:

```text
.env
data/resume_agent.db
data/*.db-wal
data/*.db-shm
data/resumes/
frontend/node_modules/
Python __pycache__/
```

The following files are required for source delivery and should remain in Git:

```text
.env.example
backend/requirements.txt
backend/alembic/
backend/alembic.ini
frontend/package.json
frontend/package-lock.json
```

## 14. Recommended First Test

After completing the setup, verify the application using the following sequence:

1. Start the FastAPI backend.
2. Start the Vue frontend.
3. Open `http://127.0.0.1:12140/login`.
4. Log in using the user created with `manage_user.py`.
5. Create or parse a Job Description.
6. Upload a PDF resume.
7. Run resume parsing.
8. Run candidate-job scoring.
9. Run Talent Discovery.
10. Open the candidate result and verify the analysis.

If real LLM mode is enabled, valid LLM configuration is required for the AI-related steps.

## 15. Common Issues

### Login succeeds but the application returns 401

Check:

```env
COOKIE_SECURE=false
```

for local HTTP development.

### AI functions return model configuration errors

Check:

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

Also verify that the corresponding module is not incorrectly configured for real LLM mode.

### Frontend cannot start

Check the Node.js version:

```powershell
node --version
```

Use Node.js 22.12.0 or later.

Then reinstall from the lock file:

```powershell
npm ci
```

### Database has not been initialized

Run:

```powershell
cd backend
python -m alembic upgrade head
```

### No login account exists

Create one:

```powershell
cd backend
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

## 16. Current Scope

The current RA implementation is intended primarily for local/internal application use and project demonstration.

The repository currently provides a Vite-based frontend development environment and FastAPI backend runtime.

Production deployment infrastructure, such as a reverse proxy, HTTPS termination, container orchestration, or production frontend hosting, is outside the current project scope.
