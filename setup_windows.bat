@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
set "CONDA_ENV=resume_agent_py310"

echo ============================================================
echo Resume Agent - Windows First-Time Setup
echo Project root: %PROJECT_ROOT%
echo ============================================================
echo.

pushd "%PROJECT_ROOT%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Cannot access the project directory.
    goto :failure
)

where conda >nul 2>&1
if errorlevel 1 (
    echo Conda not found. Please install Miniconda or Anaconda.
    goto :failure_with_popd
)

echo [1/7] Checking Conda environment %CONDA_ENV%...
conda env list 2>nul | findstr /B /C:"%CONDA_ENV% " >nul
if errorlevel 1 (
    echo Creating Conda environment %CONDA_ENV% with Python 3.10...
    call conda create -n "%CONDA_ENV%" python=3.10 -y
    if errorlevel 1 (
        echo ERROR: Failed to create Conda environment %CONDA_ENV%.
        goto :failure_with_popd
    )
) else (
    echo Conda environment %CONDA_ENV% already exists. Skipping creation.
)

echo [2/7] Activating Conda environment %CONDA_ENV%...
call conda activate "%CONDA_ENV%"
if errorlevel 1 (
    echo ERROR: Failed to activate Conda environment %CONDA_ENV%.
    goto :failure_with_popd
)

echo [3/7] Installing backend dependencies...
python -m pip install -r "backend\requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies.
    goto :failure_with_popd
)

echo [4/7] Preparing project configuration...
if exist ".env" (
    echo Existing .env found. It will not be overwritten.
) else (
    if not exist ".env.example" (
        echo ERROR: .env.example was not found.
        goto :failure_with_popd
    )
    copy ".env.example" ".env" >nul
    if errorlevel 1 (
        echo ERROR: Failed to create .env from .env.example.
        goto :failure_with_popd
    )
    echo Created .env from .env.example.
    echo Real AI mode requires valid LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL values.
)

if not exist "data" (
    mkdir "data"
    if errorlevel 1 (
        echo ERROR: Failed to create the data directory.
        goto :failure_with_popd
    )
)

echo [5/7] Applying database migrations...
pushd "backend" >nul 2>&1
if errorlevel 1 (
    echo ERROR: backend directory was not found.
    goto :failure_with_popd
)
python -m alembic upgrade head
set "ALEMBIC_EXIT=!ERRORLEVEL!"
popd
if not "!ALEMBIC_EXIT!"=="0" (
    echo ERROR: Database migration failed.
    goto :failure_with_popd
)

echo [6/7] Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo Node.js not found. Please install Node.js 22.12.0 or later.
    goto :failure_with_popd
)

where npm >nul 2>&1
if errorlevel 1 (
    echo npm not found. Please install Node.js 22.12.0 or later.
    goto :failure_with_popd
)

for /f "tokens=1,2 delims=." %%A in ('node -p "process.versions.node"') do (
    set "NODE_MAJOR=%%A"
    set "NODE_MINOR=%%B"
)

echo Current Node.js version:
node --version

if not defined NODE_MAJOR (
    echo ERROR: Unable to determine the Node.js version.
    goto :failure_with_popd
)
if !NODE_MAJOR! LSS 22 (
    echo ERROR: Node.js 22.12.0 or later is required.
    goto :failure_with_popd
)
if !NODE_MAJOR! EQU 22 if !NODE_MINOR! LSS 12 (
    echo ERROR: Node.js 22.12.0 or later is required.
    goto :failure_with_popd
)

echo [7/7] Installing frontend dependencies with npm ci...
pushd "frontend" >nul 2>&1
if errorlevel 1 (
    echo ERROR: frontend directory was not found.
    goto :failure_with_popd
)
npm ci
set "NPM_EXIT=!ERRORLEVEL!"
popd
if not "!NPM_EXIT!"=="0" (
    echo ERROR: Frontend dependency installation failed.
    goto :failure_with_popd
)

echo.
echo ============================================================
echo Setup completed successfully.
echo ============================================================
echo.
echo Manual step A - Real AI configuration:
echo   Edit "%PROJECT_ROOT%.env" and provide valid values for:
echo   LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL.
echo.
echo Manual step B - Create the first user:
echo   conda activate %CONDA_ENV%
echo   cd /d "%PROJECT_ROOT%backend"
echo   python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
echo.
echo The password is entered interactively and is not stored in this script.
echo After completing the required manual steps, double-click start_ra.bat.
echo.
popd
pause
exit /b 0

:failure_with_popd
popd

:failure
echo.
echo Setup stopped because of the error above.
pause
exit /b 1
