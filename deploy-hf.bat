@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

echo [1/6] Checking working tree...
git diff --quiet && git diff --cached --quiet
if errorlevel 1 (
    echo ERROR: Working tree has uncommitted changes. Commit or stash first.
    exit /b 1
)

for /f %%i in ('git rev-parse --short HEAD') do set MAIN_SHA=%%i
echo Main commit: %MAIN_SHA%

echo [2/6] Removing old deploy branch if exists...
git branch -D hf-deploy-snap 2>nul

echo [3/6] Creating orphan snapshot branch...
git checkout --orphan hf-deploy-snap
if errorlevel 1 (
    echo ERROR: Failed to create orphan branch.
    exit /b 1
)

git add -A

echo [4/6] Checking for forbidden binaries...
git diff --cached --name-only | findstr /i /r "\.bin$ screenshots" >nul
if not errorlevel 1 (
    echo ERROR: Staged files contain .bin or screenshots. Aborting.
    git checkout main 2>nul
    git branch -D hf-deploy-snap 2>nul
    exit /b 1
)

git commit -m "HF Space deploy snapshot from main (%MAIN_SHA%)."
if errorlevel 1 (
    echo ERROR: Commit failed.
    git checkout main 2>nul
    exit /b 1
)

echo [5/6] Pushing to Hugging Face Space...
git push hf hf-deploy-snap:main --force
set PUSH_OK=!errorlevel!

echo [6/6] Restoring main branch...
git checkout main
git branch -D hf-deploy-snap

if !PUSH_OK! neq 0 (
    echo ERROR: HF push failed.
    exit /b 1
)

echo.
echo Done. HF Space is rebuilding from snapshot of main (%MAIN_SHA%).
echo Logs: https://huggingface.co/spaces/proaugust/cur_index
endlocal
