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

使用 [uv](https://docs.astral.sh/uv/) + Python 3.13（`D:\Program Files\Python\cpython-3.13.14-windows-x86_64-none`）：

```bash
# 首次：创建 .venv 并安装依赖
uv sync --python "D:\Program Files\Python\cpython-3.13.14-windows-x86_64-none\python.exe"

# 新增依赖后
uv add <package>
# 或编辑 pyproject.toml 后
uv sync
```

数据库使用 PostgreSQL，连接串写在 `.env` 的 `DATABASE_URL`。

## 启动

```bash
uv run uvicorn app.main:app --reload
# 或
uv run python -m app.main
```

访问 http://127.0.0.1:8000/docs 查看 API 文档。

## 启动前端
cd d:\code\py\demo\cur_index\vue-manage-system-master
npm install
npm run dev