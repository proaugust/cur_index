@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

where git >nul 2>&1
if errorlevel 1 (
    echo ERROR: git not found in PATH.
    goto :fail
)

echo [1/5] Ensuring on main...
for /f "delims=" %%i in ('git branch --show-current') do set CUR_BRANCH=%%i
if /I not "!CUR_BRANCH!"=="main" (
    echo Switching !CUR_BRANCH! -^> main
    git checkout main
    if errorlevel 1 goto :fail
)

echo [2/5] Auto-commit if dirty...
git add -A
git diff --cached --quiet
if errorlevel 1 (
    for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH:mm"') do set TS=%%i
    git commit -m "chore: auto snapshot before deploy (!TS!)"
    if errorlevel 1 goto :fail
    echo Committed pending changes.
) else (
    echo Working tree clean, skip commit.
)

for /f %%i in ('git rev-parse --short HEAD') do set SHA=%%i
echo On main @ !SHA!

echo [3/5] Pushing GitHub main...
git push origin main
if errorlevel 1 goto :fail

echo [4/5] Syncing GitHub dev from main...
git push origin main:dev
if errorlevel 1 goto :fail

echo [5/5] Deploying Hugging Face Space...
call "%~dp0deploy-hf.bat"
if errorlevel 1 goto :fail

echo.
echo Done. origin/main + origin/dev updated; HF deploy from !SHA!.
echo Logs: https://huggingface.co/spaces/proaugust/cur_index
pause
endlocal
exit /b 0

:fail
echo.
echo FAILED. See messages above.
@REM pause
endlocal
exit /b 1
