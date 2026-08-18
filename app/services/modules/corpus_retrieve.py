"""切块检索：向量 / 全文 / hybrid + C1 融合重排 + Parent 扩节（通用 / 业务表）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.modules.chunk_lang import (
    ChunkLang,
    DEFAULT_CHUNK_LANG,
    normalize_lang,
    prepare_query_text,
    ts_config,
)
from app.services.modules.chunk_table_ops import (
    BUSINESS_CHUNK_TABLE,
    GENERAL_CHUNK_TABLE,
    get_chunk_model,
    row_to_dict,
    source_file_like_pattern,
)
from app.services.shared.embedding import embed_query

_RETRIEVE_MODES = frozenset({"vector", "hybrid", "hybrid_rerank"})
_DEFAULT_RECALL_K = 30
_PARENT_MAX_CHARS = 1500
_W_VECTOR, _W_FTS, _W_TITLE, _W_PATH = 0.55, 0.35, 0.07, 0.03


@dataclass
class RetrievedHit:
    row: Any
    vector_sim: float = 0.0
    fts_rank: float = 0.0
    fusion_score: float = 0.0
    from_vector: bool = False
    from_fts: bool = False
    expanded_content: str | None = None


def _normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [1.0 if v > 0 else 0.0 for v in values]
    return [(v - lo) / (hi - lo) for v in values]


def _title_path_bonus(query: str, title: str, path: str) -> tuple[float, float]:
    q = query.strip().lower()
    if not q:
        return 0.0, 0.0
    title_l, path_l = (title or "").lower(), (path or "").lower()
    title_hit = 1.0 if q in title_l else 0.0
    path_hit = 1.0 if q in path_l else 0.0
    for tok in (t for t in re.split(r"\s+", q) if len(t) >= 2):
        if not title_hit and tok in title_l:
            title_hit = 0.7
        if not path_hit and tok in path_l:
            path_hit = 0.7
    return title_hit, path_hit


def recall_vector(
    db: Session,
    query: str,
    *,
    table_name: str,
    recall_k: int,
    source_file: str | None,
    lang: ChunkLang,
    corpus_name: str | None = None,
) -> list[RetrievedHit]:
    model = get_chunk_model(table_name)
    query_vector = embed_query(query.strip())
    distance_expr = model.embedding.cosine_distance(query_vector).label("distance")
    q = db.query(model, distance_expr).filter(model.embedding.isnot(None)).filter(model.lang == lang)
    if corpus_name is not None:
        q = q.filter(model.corpus_name == corpus_name)
    file_pattern = source_file_like_pattern(source_file)
    if file_pattern:
        q = q.filter(model.source_file.ilike(file_pattern))
    rows = q.order_by(distance_expr).limit(recall_k).all()
    return [
        RetrievedHit(row=chunk, vector_sim=round(1 - distance, 4), from_vector=True)
        for chunk, distance in rows
    ]


def recall_fts(
    db: Session,
    query: str,
    *,
    table_name: str,
    recall_k: int,
    source_file: str | None,
    lang: ChunkLang,
    corpus_name: str | None = None,
) -> list[RetrievedHit]:
    prepared = prepare_query_text(query, lang)
    if not prepared:
        return []
    cfg = ts_config(lang)
    params: dict[str, Any] = {"q": prepared, "limit": recall_k, "lang": lang}
    extra = ""
    if corpus_name is not None:
        extra += " AND corpus_name = :corpus_name"
        params["corpus_name"] = corpus_name
    file_pattern = source_file_like_pattern(source_file)
    if file_pattern:
        extra += " AND source_file ILIKE :source_file_pattern"
        params["source_file_pattern"] = file_pattern
    sql = text(
        f"""
        SELECT id, ts_rank_cd(search_vector, query) AS rank
        FROM {table_name}, plainto_tsquery('{cfg}', :q) AS query
        WHERE search_vector IS NOT NULL AND search_vector @@ query AND lang = :lang {extra}
        ORDER BY rank DESC LIMIT :limit
        """
    )
    ranked = db.execute(sql, params).fetchall()
    if not ranked:
        return []
    model = get_chunk_model(table_name)
    ids = [int(r[0]) for r in ranked]
    rank_map = {int(r[0]): float(r[1] or 0.0) for r in ranked}
    by_id = {c.id: c for c in db.query(model).filter(model.id.in_(ids)).all()}
    return [
        RetrievedHit(row=by_id[cid], fts_rank=rank_map[cid], from_fts=True)
        for cid in ids
        if cid in by_id
    ]


def merge_hits(vector_hits: list[RetrievedHit], fts_hits: list[RetrievedHit]) -> list[RetrievedHit]:
    merged: dict[int, RetrievedHit] = {h.row.id: h for h in vector_hits}
    for hit in fts_hits:
        existing = merged.get(hit.row.id)
        if existing is None:
            merged[hit.row.id] = hit
            continue
        existing.fts_rank = hit.fts_rank
        existing.from_fts = True
    return list(merged.values())


def fusion_rerank(query: str, hits: list[RetrievedHit]) -> list[RetrievedHit]:
    """C1：归一化向量分 + 全文分 + 标题/路径命中加权。"""
    if not hits:
        return []
    v_norms = _normalize_scores([h.vector_sim for h in hits])
    f_norms = _normalize_scores([h.fts_rank for h in hits])
    for i, hit in enumerate(hits):
        title_b, path_b = _title_path_bonus(query, hit.row.section_title, hit.row.section_path)
        hit.fusion_score = round(
            _W_VECTOR * v_norms[i] + _W_FTS * f_norms[i] + _W_TITLE * title_b + _W_PATH * path_b,
            6,
        )
    hits.sort(key=lambda h: (h.fusion_score, h.vector_sim, h.fts_rank), reverse=True)
    return hits


def display_similarity(hit: RetrievedHit, *, use_fusion: bool) -> float:
    if use_fusion and hit.fusion_score > 0:
        return round(hit.fusion_score, 4)
    if hit.vector_sim > 0:
        return hit.vector_sim
    return round(min(0.99, 0.5 + hit.fts_rank), 4)


def expand_parents(
    db: Session,
    hits: list[RetrievedHit],
    *,
    table_name: str,
    corpus_name: str | None = None,
    max_chars: int = _PARENT_MAX_CHARS,
) -> list[RetrievedHit]:
    """按 section_path 拼同节上下文到 expanded_content；同节只保留一条。"""
    if not hits:
        return []
    model = get_chunk_model(table_name)
    seen: set[tuple[str, str]] = set()
    out: list[RetrievedHit] = []
    for hit in hits:
        key = (hit.row.source_file, hit.row.section_path or "")
        if key in seen:
            continue
        seen.add(key)
        q = (
            db.query(model)
            .filter(model.source_file == hit.row.source_file)
            .filter(model.section_path == hit.row.section_path)
        )
        if corpus_name is not None:
            q = q.filter(model.corpus_name == corpus_name)
        siblings = q.order_by(model.chunk_index, model.id).all()
        if len(siblings) <= 1:
            out.append(hit)
            continue
        parts: list[str] = []
        total = 0
        for sib in siblings:
            piece = sib.content or ""
            if total + len(piece) > max_chars and parts:
                break
            parts.append(piece)
            total += len(piece) + 2
        hit.expanded_content = "\n\n".join(parts)
        out.append(hit)
    return out


def retrieve(
    db: Session,
    query: str,
    *,
    table_name: str = BUSINESS_CHUNK_TABLE,
    corpus_name: str | None = None,
    limit: int = 5,
    min_similarity: float = 0.55,
    source_file: str | None = None,
    retrieve_mode: str = "hybrid",
    recall_k: int = _DEFAULT_RECALL_K,
    expand_parent: bool = False,
    lang: str | None = None,
) -> list[dict[str, Any]]:
    mode = (retrieve_mode or "hybrid").strip().lower()
    if mode not in _RETRIEVE_MODES:
        raise ValueError(f"不支持的 retrieve_mode: {retrieve_mode}")
    if table_name == BUSINESS_CHUNK_TABLE and not corpus_name:
        raise ValueError("业务知识库检索必须指定 corpus_name")
    if table_name == GENERAL_CHUNK_TABLE:
        corpus_name = None

    resolved_lang = normalize_lang(lang or DEFAULT_CHUNK_LANG)
    use_fts = mode in ("hybrid", "hybrid_rerank")
    use_fusion = mode in ("hybrid", "hybrid_rerank")
    k = max(limit, min(recall_k, 50))
    common = dict(
        table_name=table_name,
        recall_k=k,
        source_file=source_file,
        lang=resolved_lang,
        corpus_name=corpus_name,
    )
    vector_hits = recall_vector(db, query, **common)
    fts_hits = recall_fts(db, query, **common) if use_fts else []
    hits = merge_hits(vector_hits, fts_hits) if use_fts else list(vector_hits)

    if use_fusion:
        hits = fusion_rerank(query, hits)
    else:
        hits.sort(key=lambda h: h.vector_sim, reverse=True)

    filtered: list[RetrievedHit] = []
    for hit in hits:
        if hit.from_vector and hit.vector_sim >= min_similarity:
            filtered.append(hit)
        elif hit.from_fts:
            filtered.append(hit)
    hits = filtered[:limit]
    if expand_parent:
        hits = expand_parents(db, hits, table_name=table_name, corpus_name=corpus_name)

    results: list[dict[str, Any]] = []
    for hit in hits:
        item = row_to_dict(hit.row)
        if hit.expanded_content is not None:
            item["content"] = hit.expanded_content
            item["char_count"] = len(hit.expanded_content)
        item["similarity"] = display_similarity(hit, use_fusion=use_fusion)
        results.append(item)
    return results
