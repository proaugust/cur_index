"""业务资料库分类常量与轻量推荐。"""

from __future__ import annotations

CORPUS_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("policy", "政策制度"),
    ("product", "产品说明"),
    ("support", "客服话术"),
    ("legal", "合同法务"),
    ("report", "研究报告"),
    ("other", "其他"),
)
DEFAULT_CATEGORY = "other"
VALID_CATEGORIES = {c for c, _ in CORPUS_CATEGORIES}

KEYWORD_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("policy", ("制度", "规章", "政策", "考勤", "请假", "报销", "手册")),
    ("product", ("产品", "型号", "规格", "功能", "说明书", "参数")),
    ("support", ("客服", "投诉", "退换", "售后", "话术", "FAQ", "常见问题")),
    ("legal", ("合同", "条款", "合规", "违约", "保密", "协议", "审计")),
    ("report", ("财报", "报告", "研究", "分析", "趋势", "总结")),
)


def normalize_category(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in VALID_CATEGORIES else DEFAULT_CATEGORY


def list_category_options() -> list[dict[str, str]]:
    return [{"value": v, "label": label} for v, label in CORPUS_CATEGORIES]


def suggest_category(question: str) -> dict[str, str | float]:
    """关键词打分推荐分类（无需 LLM）。"""
    q = (question or "").strip()
    if not q:
        return {"category": DEFAULT_CATEGORY, "label": "其他", "score": 0.0}
    best = DEFAULT_CATEGORY
    best_score = 0
    for cat, words in KEYWORD_HINTS:
        score = sum(1 for w in words if w in q)
        if score > best_score:
            best, best_score = cat, score
    label = dict(CORPUS_CATEGORIES).get(best, "其他")
    conf = min(1.0, best_score / 3.0) if best_score else 0.0
    return {"category": best, "label": label, "score": round(conf, 2)}
