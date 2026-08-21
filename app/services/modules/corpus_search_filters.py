"""业务资料库检索：多库/分类范围解析 + 规则版过滤建议。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud import document_corpora as corpus_crud
from app.services.modules.corpus_categories import CORPUS_CATEGORIES, KEYWORD_HINTS, VALID_CATEGORIES


def merge_corpus_names(
    corpus_name: str | None = None,
    corpus_names: list[str] | None = None,
) -> list[str] | None:
    out: list[str] = []
    seen: set[str] = set()
    for n in list(corpus_names or []) + ([corpus_name] if corpus_name else []):
        s = (n or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out or None


def apply_corpus_name_filter(q, model, names: list[str] | None):
    if names is None:
        return q
    if len(names) == 1:
        return q.filter(model.corpus_name == names[0])
    return q.filter(model.corpus_name.in_(names))


def split_csv(value: str | None) -> list[str]:
    if not value or not str(value).strip():
        return []
    return [p.strip() for p in str(value).split(",") if p.strip()]


def resolve_corpus_names(
    db: Session,
    *,
    corpus_name: str | None = None,
    corpus_names: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[str] | None:
    """None=全库；非空 list=限定；空 list=有过滤但无匹配资料库。"""
    cats = [c.strip().lower() for c in (categories or []) if c and c.strip()]
    cats = [c for c in cats if c in VALID_CATEGORIES]
    names_in = [n.strip() for n in (corpus_names or []) if n and n.strip()]
    single = (corpus_name or "").strip()
    if single:
        names_in.append(single)

    if not cats and not names_in:
        return None

    ordered: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)

    for cat in cats:
        for row in corpus_crud.list_corpora(db, category=cat):
            _add(row.name)
    for name in names_in:
        row = corpus_crud.get_corpus_by_name(db, name)
        if row is not None:
            _add(row.name)
    return ordered


def suggest_search_filters(db: Session, question: str) -> dict:
    """关键词规则建议分类/资料库；无把握则留空（表示全库混搜）。"""
    q = (question or "").strip()
    if not q:
        return {
            "categories": [],
            "corpus_names": [],
            "source_file": None,
            "retrieve_mode": "hybrid",
            "rationale": "未提供问题，不过滤。",
        }

    scored: list[tuple[str, int]] = []
    for cat, words in KEYWORD_HINTS:
        score = sum(1 for w in words if w in q)
        if score > 0:
            scored.append((cat, score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    categories = [c for c, s in scored if s > 0][:3]

    all_corpora = corpus_crud.list_corpora(db)
    names: list[str] = []
    seen: set[str] = set()
    q_lower = q.lower()

    for row in all_corpora:
        name = row.name
        if name.lower() in q_lower or (len(name) >= 2 and name in q):
            if name not in seen:
                seen.add(name)
                names.append(name)

    if categories:
        cat_set = set(categories)
        for row in all_corpora:
            if getattr(row, "category", None) in cat_set and row.name not in seen:
                seen.add(row.name)
                names.append(row.name)

    label_map = dict(CORPUS_CATEGORIES)
    if categories or names:
        cat_txt = "、".join(label_map.get(c, c) for c in categories) or "未指定"
        rationale = f"根据问题关键词建议分类「{cat_txt}」，资料库 {len(names)} 个；可手动修改后再检索。"
    else:
        rationale = "未匹配到明确分类/资料库，建议全库混合检索；也可手动勾选过滤。"

    return {
        "categories": categories,
        "corpus_names": names[:20],
        "source_file": None,
        "retrieve_mode": "hybrid",
        "rationale": rationale,
    }


def normalize_category_list(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for v in values or []:
        raw = (v or "").strip().lower()
        if raw in VALID_CATEGORIES and raw not in out:
            out.append(raw)
    return out
