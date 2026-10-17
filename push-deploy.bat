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

echo [2/5] Commit if dirty...
git add -A
git diff --cached --quiet
if errorlevel 1 (
    echo.
    echo Pending changes to commit:
    git diff --cached --stat
    echo.

    rem Auto-summary from staged paths -^> %TEMP%\push-deploy-subject.txt
    powershell -NoProfile -Command ^
      "$lines = git diff --cached --name-status; $names=@(); $a=0; $m=0; $d=0;" ^
      "foreach ($line in $lines) {" ^
      "  if ($line -match '^(A|M|D)\t(.+)$') { $names += $Matches[2]; switch ($Matches[1]) { 'A'{$a++} 'M'{$m++} 'D'{$d++} } }" ^
      "  elseif ($line -match '^R\d+\t.+\t(.+)$') { $names += $Matches[1]; $m++ }" ^
      "};" ^
      "$n=$names.Count; $hint=(($names | ForEach-Object { Split-Path $_ -Leaf } | Select-Object -First 3) -join ', ');" ^
      "if ($n -gt 3) { $hint += ', +' + ($n-3) + ' more' };" ^
      "if ($a -gt 0 -and $m -eq 0 -and $d -eq 0) { $p='feat: add' }" ^
      "elseif ($d -gt 0 -and $a -eq 0 -and $m -eq 0) { $p='chore: remove' }" ^
      "else { $p='chore: update' };" ^
      "[IO.File]::WriteAllText($env:TEMP + '\push-deploy-subject.txt', ($p + ' ' + $hint))"
    if errorlevel 1 goto :fail

    set /p COMMIT_MSG=<"%TEMP%\push-deploy-subject.txt"
    echo Suggested commit message:
    echo   !COMMIT_MSG!
    echo.
    set EDIT=
    set /p EDIT=Edit this message? [y/N]:
    if /I "!EDIT!"=="y" (
        set /p COMMIT_MSG=New message:
        if "!COMMIT_MSG!"=="" (
            echo ERROR: empty commit message; abort deploy.
            goto :fail
        )
    )

    for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH:mm"') do set TS=%%i
    git diff --cached --stat > "%TEMP%\push-deploy-stat.txt"
    (
        echo !COMMIT_MSG!
        echo.
        echo Snapshot before deploy ^(!TS!^).
        echo.
        type "%TEMP%\push-deploy-stat.txt"
    ) > "%TEMP%\push-deploy-msg.txt"
    git commit -F "%TEMP%\push-deploy-msg.txt"
    if errorlevel 1 goto :fail
    del "%TEMP%\push-deploy-subject.txt" "%TEMP%\push-deploy-stat.txt" "%TEMP%\push-deploy-msg.txt" 2>nul
    echo Committed: !COMMIT_MSG!
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
endlocal
exit /b 1
