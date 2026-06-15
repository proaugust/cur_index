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

依赖统一装在 conda 环境 `cur_index` 下（不在项目目录里建 venv）：

```bash
conda env create -f environment.yml   # 首次
conda activate cur_index
pip install -r requirements.txt       # 新增依赖后
```

数据库使用 PostgreSQL，连接串写在 `.env` 的 `DATABASE_URL`。

## 启动

```bash
conda activate cur_index
uvicorn app.main:app --reload
```

访问 http://127.0.0.1:8000/docs 查看 API 文档。
