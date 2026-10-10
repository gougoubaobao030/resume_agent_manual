@echo off
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0"
set "CONDA_ENV=resume_agent_py310"

pushd "%PROJECT_ROOT%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Cannot access the project directory.
    goto :failure
)

where conda >nul 2>&1
if errorlevel 1 (
    echo Conda not found. Please install Miniconda or Anaconda, then run setup_windows.bat.
    goto :failure_with_popd
)

conda env list 2>nul | findstr /B /C:"%CONDA_ENV% " >nul
if errorlevel 1 (
    echo Conda environment %CONDA_ENV% was not found. Please run setup_windows.bat first.
    goto :failure_with_popd
)

call conda activate "%CONDA_ENV%"
if errorlevel 1 (
    echo ERROR: Failed to activate Conda environment %CONDA_ENV%.
    echo Please run setup_windows.bat first.
    goto :failure_with_popd
)

if not exist ".env" (
    echo .env was not found. Please run setup_windows.bat first.
    goto :failure_with_popd
)

where node >nul 2>&1
if errorlevel 1 (
    echo Node.js not found. Please install Node.js 22.12.0 or later and run setup_windows.bat.
    goto :failure_with_popd
)

where npm >nul 2>&1
if errorlevel 1 (
    echo npm not found. Please install Node.js 22.12.0 or later and run setup_windows.bat.
    goto :failure_with_popd
)

echo Starting Resume Agent backend...
start "RA Backend" /D "%PROJECT_ROOT%backend" cmd.exe /k "call conda activate %CONDA_ENV% && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18000"

echo Starting Resume Agent frontend...
start "RA Frontend" /D "%PROJECT_ROOT%frontend" cmd.exe /k "npm run dev"

echo Waiting briefly before opening the browser...
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:12140/login"

echo Resume Agent launch commands were opened in separate windows.
popd
exit /b 0

:failure_with_popd
popd

:failure
echo.
echo Startup stopped because of the error above.
pause
exit /b 1
