"""按 slug 动态创建 / 绑定 document_{slug}_chunk 物理表。"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text, bindparam, inspect, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.config import settings
from app.database import Base

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_TABLE_RE = re.compile(r"^document_[a-z][a-z0-9_]{0,47}_chunk$")
_model_cache: dict[str, type] = {}
# 大批量插入时先卸 HNSW，写完再建，阈值按行数
HNSW_BULK_THRESHOLD = 500


def hnsw_index_name(table_name: str) -> str:
    return f"ix_dcc_{table_name[len('document_'):-len('_chunk')]}_hnsw"[:63]


def source_index_name(table_name: str) -> str:
    return f"ix_dcc_{table_name[len('document_'):-len('_chunk')]}_src"[:63]


def fts_index_name(table_name: str) -> str:
    return f"ix_dcc_{table_name[len('document_'):-len('_chunk')]}_fts"[:63]


def _cjk_spaced_sql(col: str) -> str:
    """中文按字插空格，便于 simple 配置的 tsvector 分词。"""
    return f"regexp_replace(coalesce({col}, ''), '([一-龥])', '\\1 ', 'g')"


def search_vector_sql_expr() -> str:
    title = _cjk_spaced_sql("section_title")
    path = _cjk_spaced_sql("section_path")
    body = _cjk_spaced_sql("content")
    return (
        f"setweight(to_tsvector('simple', {title}), 'A') || "
        f"setweight(to_tsvector('simple', {path}), 'A') || "
        f"setweight(to_tsvector('simple', {body}), 'B')"
    )


def name_to_slug(name: str) -> str:
    raw = name.strip().lower()
    ascii_part = re.sub(r"[^a-z0-9]+", "_", raw)
    ascii_part = re.sub(r"_+", "_", ascii_part).strip("_")
    if ascii_part and _SLUG_RE.match(ascii_part):
        return ascii_part[:48]
    digest = hashlib.sha1(name.strip().encode("utf-8")).hexdigest()[:10]
    if ascii_part:
        base = re.sub(r"[^a-z0-9_]", "", ascii_part)[:30].strip("_")
        candidate = f"{base}_{digest[:4]}" if base else f"c_{digest}"
    else:
        candidate = f"c_{digest}"
    if not candidate[0].isalpha():
        candidate = f"c_{candidate}"
    return candidate[:48]


def table_name_for_slug(slug: str) -> str:
    if not _SLUG_RE.match(slug):
        raise ValueError(f"非法 table_slug: {slug}")
    return f"document_{slug}_chunk"


def ensure_chunk_table(db: Session, table_name: str) -> None:
    """若不存在则创建切块表；已存在则补齐 FTS 列/索引。"""
    if not _TABLE_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name}")
    engine = db.get_bind()
    if table_name not in inspect(engine).get_table_names():
        dim = settings.embedding_dim
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        source_file VARCHAR(500) NOT NULL,
                        section_title VARCHAR(500) NOT NULL DEFAULT '',
                        section_path VARCHAR(500) NOT NULL DEFAULT '',
                        chunk_index INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        char_count INTEGER NOT NULL,
                        embedding vector({dim}),
                        search_vector tsvector
                    )
                    """
                )
            )
            idx_src = source_index_name(table_name)
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_src} ON {table_name} (source_file)"))
            conn.execute(text(_create_hnsw_sql(table_name)))
            conn.execute(text(_create_fts_sql(table_name)))
        logger.info("已创建切块表 %s", table_name)
        return
    ensure_chunk_fts(db, table_name)


def ensure_chunk_fts(db: Session, table_name: str) -> None:
    """为已有切块表补齐 search_vector + GIN（幂等）。"""
    if not _TABLE_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name}")
    engine = db.get_bind()
    cols = {c["name"] for c in inspect(engine).get_columns(table_name)}
    expr = search_vector_sql_expr()
    with engine.begin() as conn:
        if "search_vector" not in cols:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN search_vector tsvector"))
            logger.info("已为 %s 添加 search_vector", table_name)
        conn.execute(text(f"UPDATE {table_name} SET search_vector = {expr} WHERE search_vector IS NULL"))
        conn.execute(text(_create_fts_sql(table_name)))


def refresh_search_vectors(db: Session, table_name: str, *, source_files: list[str] | None = None) -> None:
    """重算 search_vector（导入后调用）。"""
    if not _TABLE_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name}")
    expr = search_vector_sql_expr()
    if source_files:
        stmt = text(
            f"UPDATE {table_name} SET search_vector = {expr} WHERE source_file IN :files"
        ).bindparams(bindparam("files", expanding=True))
        db.execute(stmt, {"files": list(source_files)})
    else:
        db.execute(text(f"UPDATE {table_name} SET search_vector = {expr} WHERE search_vector IS NULL"))


def _create_hnsw_sql(table_name: str) -> str:
    idx = hnsw_index_name(table_name)
    return (
        f"CREATE INDEX IF NOT EXISTS {idx} "
        f"ON {table_name} USING hnsw (embedding vector_cosine_ops) "
        f"WHERE embedding IS NOT NULL"
    )


def _create_fts_sql(table_name: str) -> str:
    idx = fts_index_name(table_name)
    return f"CREATE INDEX IF NOT EXISTS {idx} ON {table_name} USING gin (search_vector)"


def drop_hnsw_index(db: Session, table_name: str) -> None:
    if not _TABLE_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name}")
    db.execute(text(f"DROP INDEX IF EXISTS {hnsw_index_name(table_name)}"))


def create_hnsw_index(db: Session, table_name: str) -> None:
    if not _TABLE_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name}")
    db.execute(text(_create_hnsw_sql(table_name)))


def get_chunk_model(table_name: str) -> type:
    """返回绑定到指定物理表的动态 ORM 类（带缓存）。"""
    if not _TABLE_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name}")
    cached = _model_cache.get(table_name)
    if cached is not None:
        return cached

    dim = settings.embedding_dim
    class_name = f"DynDocChunk_{table_name}"
    model = type(
        class_name,
        (Base,),
        {
            "__tablename__": table_name,
            "__table_args__": {"extend_existing": True},
            "id": mapped_column(Integer, primary_key=True),
            "source_file": mapped_column(String(500), index=True),
            "section_title": mapped_column(String(500), default=""),
            "section_path": mapped_column(String(500), default=""),
            "chunk_index": mapped_column(Integer),
            "content": mapped_column(Text),
            "char_count": mapped_column(Integer),
            "embedding": mapped_column(Vector(dim), nullable=True),
            "__annotations__": {
                "id": Mapped[int],
                "source_file": Mapped[str],
                "section_title": Mapped[str],
                "section_path": Mapped[str],
                "chunk_index": Mapped[int],
                "content": Mapped[str],
                "char_count": Mapped[int],
                "embedding": Mapped[list[float] | None],
            },
        },
    )
    _model_cache[table_name] = model
    return model


def embedding_preview(embedding: Any, *, head: int = 4) -> str | None:
    """仅展示前几维 + 总维数，避免把 512 维整列回给前端。"""
    if embedding is None:
        return None
    try:
        vals = list(embedding)
    except TypeError:
        return None
    if not vals:
        return None
    head_s = ", ".join(f"{float(x):.3f}" for x in vals[:head])
    return f"[{head_s}, …] ×{len(vals)}"


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "source_file": row.source_file,
        "section_title": row.section_title,
        "section_path": row.section_path,
        "chunk_index": row.chunk_index,
        "content": row.content,
        "char_count": row.char_count,
        "embedding_preview": embedding_preview(getattr(row, "embedding", None)),
    }
