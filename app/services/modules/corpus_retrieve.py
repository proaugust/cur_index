"""业务知识库检索：向量 / 全文 / hybrid + C1 融合重排 + Parent 扩节。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.modules.chunk_table_ops import get_chunk_model, row_to_dict
from app.services.shared.embedding import embed_query

_CJK = re.compile(r"([\u4e00-\u9fff])")
_RETRIEVE_MODES = frozenset({"vector", "hybrid", "hybrid_rerank"})
_DEFAULT_RECALL_K = 30
_PARENT_MAX_CHARS = 1500
_W_VECTOR = 0.55
_W_FTS = 0.35
_W_TITLE = 0.07
_W_PATH = 0.03


@dataclass
class RetrievedHit:
    row: Any
    vector_sim: float = 0.0
    fts_rank: float = 0.0
    fusion_score: float = 0.0
    from_vector: bool = False
    from_fts: bool = False
    expanded_content: str | None = None


def space_cjk(text_value: str) -> str:
    if not text_value:
        return ""
    return _CJK.sub(r"\1 ", text_value).strip()


def chunk_embed_text(*, section_path: str, section_title: str, content: str) -> str:
    prefix = (section_path or section_title or "").strip()
    return f"[{prefix}] {content}" if prefix else content


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
    title_l = (title or "").lower()
    path_l = (path or "").lower()
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
    table_name: str,
    query: str,
    *,
    recall_k: int,
    source_file: str | None,
) -> list[RetrievedHit]:
    model = get_chunk_model(table_name)
    query_vector = embed_query(query.strip())
    distance_expr = model.embedding.cosine_distance(query_vector).label("distance")
    q = db.query(model, distance_expr).filter(model.embedding.isnot(None))
    if source_file:
        q = q.filter(model.source_file == source_file)
    rows = q.order_by(distance_expr).limit(recall_k).all()
    return [
        RetrievedHit(row=chunk, vector_sim=round(1 - distance, 4), from_vector=True)
        for chunk, distance in rows
    ]


def recall_fts(
    db: Session,
    table_name: str,
    query: str,
    *,
    recall_k: int,
    source_file: str | None,
) -> list[RetrievedHit]:
    spaced = space_cjk(query.strip())
    if not spaced:
        return []
    params: dict[str, Any] = {"q": spaced, "limit": recall_k}
    source_clause = ""
    if source_file:
        source_clause = "AND source_file = :source_file"
        params["source_file"] = source_file
    sql = text(
        f"""
        SELECT id, ts_rank_cd(search_vector, query) AS rank
        FROM {table_name}, plainto_tsquery('simple', :q) AS query
        WHERE search_vector IS NOT NULL
          AND search_vector @@ query
          {source_clause}
        ORDER BY rank DESC
        LIMIT :limit
        """
    )
    ranked = db.execute(sql, params).fetchall()
    if not ranked:
        return []
    model = get_chunk_model(table_name)
    ids = [int(r[0]) for r in ranked]
    rank_map = {int(r[0]): float(r[1] or 0.0) for r in ranked}
    by_id = {c.id: c for c in db.query(model).filter(model.id.in_(ids)).all()}
    hits: list[RetrievedHit] = []
    for cid in ids:
        chunk = by_id.get(cid)
        if chunk is None:
            continue
        hits.append(RetrievedHit(row=chunk, fts_rank=rank_map[cid], from_fts=True))
    return hits


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
            _W_VECTOR * v_norms[i]
            + _W_FTS * f_norms[i]
            + _W_TITLE * title_b
            + _W_PATH * path_b,
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
    table_name: str,
    hits: list[RetrievedHit],
    *,
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
        siblings = (
            db.query(model)
            .filter(model.source_file == hit.row.source_file)
            .filter(model.section_path == hit.row.section_path)
            .order_by(model.chunk_index, model.id)
            .all()
        )
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
    table_name: str,
    query: str,
    *,
    limit: int = 5,
    min_similarity: float = 0.55,
    source_file: str | None = None,
    retrieve_mode: str = "hybrid",
    recall_k: int = _DEFAULT_RECALL_K,
    expand_parent: bool = False,
) -> list[dict[str, Any]]:
    mode = (retrieve_mode or "hybrid").strip().lower()
    if mode not in _RETRIEVE_MODES:
        raise ValueError(f"不支持的 retrieve_mode: {retrieve_mode}")

    use_fts = mode in ("hybrid", "hybrid_rerank")
    use_fusion = mode in ("hybrid", "hybrid_rerank")
    k = max(limit, min(recall_k, 50))

    vector_hits = recall_vector(db, table_name, query, recall_k=k, source_file=source_file)
    fts_hits = (
        recall_fts(db, table_name, query, recall_k=k, source_file=source_file) if use_fts else []
    )
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
        hits = expand_parents(db, table_name, hits)

    results: list[dict[str, Any]] = []
    for hit in hits:
        item = row_to_dict(hit.row)
        if hit.expanded_content is not None:
            item["content"] = hit.expanded_content
            item["char_count"] = len(hit.expanded_content)
        item["similarity"] = display_similarity(hit, use_fusion=use_fusion)
        results.append(item)
    return results
