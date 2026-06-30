@echo off
cd /d %~dp0
REM 本地开发必须关闭 SERVE_STATIC，否则 API 在 /api 下，与 Vite 代理冲突导致全 404
set SERVE_STATIC=0
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-include .env
