---
title: cur_index
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# FastAPI App

纯 FastAPI 后端项目，按业务分层组织代码。

## 目录结构

```
app/
├── main.py        # 应用入口
├── core/          # 核心基础设施（配置、依赖注入、安全等）
├── database.py    # 数据库连接
├── models.py      # ORM 模型
├── schemas.py     # Pydantic 模型
├── crud.py        # 数据库操作
└── routers/       # API 路由
```

## 环境

使用 [uv](https://docs.astral.sh/uv/) + Python 3.12+：

```bash
# 首次：创建 .venv 并安装依赖
uv sync

# 新增依赖后
uv add <package>
# 或编辑 pyproject.toml 后
uv sync
```

数据库使用 PostgreSQL，连接串写在 `.env` 的 `DATABASE_URL`。

Redis 缓存（投诉统计、限流等）按环境分开配置：

| 环境 | 配置 | 说明 |
|------|------|------|
| 本地 | `.env` 不写 `REDIS_URL` | 默认 `redis://127.0.0.1:6379/0`；本机未跑 Redis 时自动降级内存缓存 |
| HF Space | Repository secrets 设 `REDIS_URL` | 使用 Upstash，格式 `rediss://default:<token>@<host>.upstash.io:6379` |

本地 `.env` 不要写入 Upstash token；token 仅放在 HF Secrets。

## 启动

```bash
uv run uvicorn app.main:app --reload
# 或
uv run python -m app.main
```

访问 http://127.0.0.1:8000/docs 查看 API 文档。

## 启动前端

在仓库根目录执行：

```bash
cd vue-manage-system-master
npm install
npm run dev
```
