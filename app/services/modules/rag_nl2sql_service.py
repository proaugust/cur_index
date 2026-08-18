"""NL2SQL 演示：Schema 检索 → 生成 SQL → 只读执行 → LLM 汇总。"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.modules.rag_prompts import STRICT_NL2SQL
from app.services.shared.llm import chat_completion

ALLOWED_TABLES = ("rag_demo_regions", "rag_demo_products", "rag_demo_sales")

SCHEMA_DOCS: tuple[dict[str, str], ...] = (
    {
        "table": "rag_demo_regions",
        "content": "区域维表。列: id, code(区域编码 east/north/south), name(华东/华北/华南，注意不含「区」字)。",
    },
    {
        "table": "rag_demo_products",
        "content": "产品维表。列: id, sku(产品编号), name(产品名), category(硬件/软件)。",
    },
    {
        "table": "rag_demo_sales",
        "content": (
            "销售事实表。列: id, sold_at(销售日期), region_code(关联 regions.code), "
            "product_sku(关联 products.sku), amount(金额), qty(数量)。"
            "问「上个月」时按 sold_at 过滤相对当前日期的上一自然月。"
        ),
    },
)

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|do)\b",
    re.I,
)


def _retrieve_schema(question: str, limit: int = 3) -> list[dict[str, str]]:
    q = question.lower()
    scored: list[tuple[int, dict[str, str]]] = []
    for doc in SCHEMA_DOCS:
        blob = f"{doc['table']} {doc['content']}".lower()
        score = sum(1 for token in re.findall(r"[\w\u4e00-\u9fff]+", q) if token in blob)
        # 销售类问题默认带上 sales
        if "销售" in question or "销售额" in question or "销量" in question:
            if doc["table"] == "rag_demo_sales":
                score += 3
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [d for s, d in scored if s > 0][:limit]
    if not picked:
        return list(SCHEMA_DOCS)
    # 保证至少含 sales 当问到金额类
    tables = {d["table"] for d in picked}
    if ("销售" in question or "额" in question) and "rag_demo_sales" not in tables:
        picked.append(SCHEMA_DOCS[2])
    return picked[:limit]


def _extract_sql(raw: str) -> str:
    text_body = raw.strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]*?)```", text_body, re.I)
    if fence:
        text_body = fence.group(1).strip()
    # 取第一条以 select 开头的语句
    match = re.search(r"(select[\s\S]+)", text_body, re.I)
    if not match:
        raise HTTPException(status_code=400, detail="未能生成合法 SELECT SQL")
    sql = match.group(1).strip().rstrip(";")
    if _FORBIDDEN.search(sql):
        raise HTTPException(status_code=400, detail="仅允许 SELECT，已拒绝危险语句")
    if ";" in sql:
        raise HTTPException(status_code=400, detail="仅允许单条 SQL")
    lower = sql.lower()
    if not lower.lstrip().startswith("select"):
        raise HTTPException(status_code=400, detail="仅允许 SELECT")

    # 纠正模型漏写的 rag_demo_ 前缀
    rewrite = {
        "regions": "rag_demo_regions",
        "products": "rag_demo_products",
        "sales": "rag_demo_sales",
    }
    for short, full in rewrite.items():
        sql = re.sub(rf"\b{short}\b", full, sql, flags=re.I)

    lower = sql.lower()
    mentioned = set(re.findall(r"\b(rag_demo_[a-z_]+)\b", lower))
    from_join = set(re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", lower))
    # FROM/JOIN 目标须为白名单表（别名不在此列）
    bad_from = {t for t in from_join if t not in set(ALLOWED_TABLES)}
    if bad_from:
        raise HTTPException(status_code=400, detail=f"禁止访问表: {', '.join(sorted(bad_from))}")
    if not mentioned:
        raise HTTPException(status_code=400, detail="SQL 未引用演示表")
    bad = mentioned - set(ALLOWED_TABLES)
    if bad:
        raise HTTPException(status_code=400, detail=f"禁止访问表: {', '.join(sorted(bad))}")
    return sql


class RagNl2sqlService:
    def __init__(self, db: Session):
        self.db = db

    def run(self, question: str, *, row_limit: int = 50) -> dict[str, Any]:
        q = (question or "").strip()
        if not q:
            raise HTTPException(status_code=400, detail="问题不能为空")
        schema_hits = _retrieve_schema(q)
        schema_block = "\n".join(f"- {h['table']}: {h['content']}" for h in schema_hits)
        user_prompt = (
            f"表结构（必须使用下列完整表名，禁止简写为 regions/products/sales）：\n"
            f"{schema_block}\n\n用户问题：{q}\n\n"
            f"请生成 PostgreSQL SELECT，只使用 rag_demo_regions / rag_demo_products / "
            f"rag_demo_sales，结果行数建议 LIMIT {row_limit}。"
        )
        raw_sql = chat_completion(
            STRICT_NL2SQL, user_prompt, temperature=0.0, disable_thinking=True, caller="rag.nl2sql"
        )
        sql = _extract_sql(raw_sql)
        # 强制上限
        if "limit" not in sql.lower():
            sql = f"{sql} LIMIT {row_limit}"
        try:
            rows = self.db.execute(text(sql)).mappings().all()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"SQL 执行失败: {exc}") from exc
        data = [dict(r) for r in rows]
        # 序列化 date/decimal
        for row in data:
            for k, v in list(row.items()):
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                elif hasattr(v, "__float__") and type(v).__name__ == "Decimal":
                    row[k] = float(v)
        summary_prompt = (
            f"用户问题：{q}\n执行 SQL：{sql}\n查询结果 JSON：{json.dumps(data, ensure_ascii=False)}\n"
            "请用简洁中文汇报结论；若结果为空请说明。"
        )
        answer = chat_completion(
            "你是数据分析助手，只依据给定查询结果回答，不要编造数字。",
            summary_prompt,
            temperature=0.2,
            disable_thinking=True,
            caller="rag.nl2sql.summary",
        )
        return {
            "question": q,
            "schema_hits": schema_hits,
            "sql": sql,
            "rows": data,
            "row_count": len(data),
            "answer": answer,
        }
