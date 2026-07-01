"""轻量数据库迁移：按文件名排序执行 app/db_migrations/ 下未跑过的脚本。

新增迁移：
  - SQL：003_short_name.sql（单条或多条以 ; 分隔）
  - Python：004_short_name.py，实现 upgrade(engine: Engine) -> None

已执行记录保存在 schema_migrations 表；本地与部署环境在启动时各跑各库，发版即同步结构。
"""

from __future__ import annotations

import importlib.util
import logging
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db_migrations"
_MIGRATION_NAME = re.compile(r"^\d{3}_[\w-]+\.(sql|py)$", re.IGNORECASE)


def _list_migration_files() -> list[Path]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    files = [path for path in MIGRATIONS_DIR.iterdir() if path.is_file() and _MIGRATION_NAME.match(path.name)]
    return sorted(files, key=lambda path: path.name)


def _ensure_migrations_table(engine: Engine) -> None:
    if "schema_migrations" in inspect(engine).get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE schema_migrations (
                    name VARCHAR(128) PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def _applied_names(engine: Engine) -> set[str]:
    _ensure_migrations_table(engine)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM schema_migrations")).fetchall()
    return {row[0] for row in rows}


def _record_migration(engine: Engine, name: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO schema_migrations (name, applied_at) VALUES (:name, :applied_at)"),
            {"name": name, "applied_at": datetime.utcnow()},
        )


def _split_sql_statements(raw: str) -> list[str]:
    statements: list[str] = []
    for chunk in raw.split(";"):
        stmt = chunk.strip()
        if not stmt:
            continue
        lines = [line for line in stmt.splitlines() if line.strip() and not line.strip().startswith("--")]
        if lines:
            statements.append("\n".join(lines))
    return statements


def _run_sql_migration(engine: Engine, path: Path) -> None:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return
    statements = _split_sql_statements(raw)
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def _run_python_migration(engine: Engine, path: Path) -> None:
    spec = importlib.util.spec_from_file_location(f"db_migration_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载迁移模块: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    upgrade = getattr(module, "upgrade", None)
    if upgrade is None:
        raise RuntimeError(f"迁移缺少 upgrade(engine): {path.name}")
    upgrade(engine)


def run_pending_migrations(engine: Engine) -> list[str]:
    """执行未记录的迁移，返回本次执行的文件名列表。"""
    applied: set[str] = set()
    try:
        applied = _applied_names(engine)
    except Exception:
        logger.exception("读取 schema_migrations 失败，将尝试创建迁移表")
        _ensure_migrations_table(engine)
        applied = _applied_names(engine)

    executed: list[str] = []
    for path in _list_migration_files():
        name = path.name
        if name in applied:
            continue
        logger.info("执行数据库迁移: %s", name)
        try:
            if path.suffix.lower() == ".sql":
                _run_sql_migration(engine, path)
            elif path.suffix.lower() == ".py":
                _run_python_migration(engine, path)
            else:
                continue
            _record_migration(engine, name)
            executed.append(name)
            logger.info("数据库迁移完成: %s", name)
        except Exception:
            logger.exception("数据库迁移失败: %s", name)
            raise
    return executed
