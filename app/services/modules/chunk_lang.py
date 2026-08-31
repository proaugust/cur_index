"""切块语言与 FTS 分词：zh / ja / en。"""

from __future__ import annotations

import re
from typing import Literal

ChunkLang = Literal["zh", "ja", "en"]
CHUNK_LANGS: tuple[ChunkLang, ...] = ("zh", "ja", "en")
DEFAULT_CHUNK_LANG: ChunkLang = "zh"

_CJK = re.compile(r"([\u4e00-\u9fff])")
_JA_CHAR = re.compile(r"([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff])")
_KANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_HAN = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[A-Za-z]")
_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]{1,}")
_EN_STOP = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "what", "how", "why", "which", "who", "where", "when",
    "to", "of", "and", "or", "for", "in", "on", "at", "it",
    "this", "that", "with", "from", "use", "using", "used",
    "can", "do", "does", "please",
})
_ZH_NOISE_PHRASES = (
    "是什么意思", "是什么", "什么是", "怎么用", "怎么样", "怎么做",
    "怎么办", "怎么", "怎样", "如何", "为何", "为什么",
    "请问", "一下", "哪个", "哪些", "哪里", "什么",
)
_ZH_NOISE_CHARS = set("的了呢吗啊呀哇么什是怎和与在有不就也还把被")


def normalize_lang(value: str | None) -> ChunkLang:
    raw = (value or DEFAULT_CHUNK_LANG).strip().lower()
    if raw in CHUNK_LANGS:
        return raw  # type: ignore[return-value]
    raise ValueError(f"lang 仅支持: {', '.join(CHUNK_LANGS)}")


def detect_lang(text: str | None, *, sample: int = 4000) -> ChunkLang:
    """根据字符分布启发式判断 zh / ja / en（无第三方依赖）。"""
    raw = (text or "").strip()
    if not raw:
        return DEFAULT_CHUNK_LANG
    snippet = raw[:sample]
    kana = len(_KANA.findall(snippet))
    han = len(_HAN.findall(snippet))
    latin = len(_LATIN.findall(snippet))
    cjk = kana + han
    if kana >= 8 or (kana >= 3 and kana * 2 >= han):
        return "ja"
    if han >= 8 or (han > 0 and han >= latin):
        return "zh"
    if latin >= 12 and latin > cjk * 2:
        return "en"
    if cjk > 0:
        return "ja" if kana > 0 else "zh"
    return "en"


def resolve_lang(explicit: str | None, text: str | None = None) -> ChunkLang:
    """显式 lang 优先；否则根据文本自动判断。"""
    if explicit and explicit.strip():
        return normalize_lang(explicit)
    return detect_lang(text)


def ts_config(lang: ChunkLang) -> str:
    return "english" if lang == "en" else "simple"


def space_cjk(text_value: str) -> str:
    if not text_value:
        return ""
    return _CJK.sub(r"\1 ", text_value).strip()


def space_ja(text_value: str) -> str:
    if not text_value:
        return ""
    return _JA_CHAR.sub(r"\1 ", text_value).strip()


def prepare_query_text(text_value: str, lang: ChunkLang) -> str:
    raw = (text_value or "").strip()
    if not raw:
        return ""
    if lang == "en":
        return raw
    if lang == "ja":
        return space_ja(raw)
    return space_cjk(raw)


def build_fts_tsquery(text_value: str, lang: ChunkLang) -> str:
    """生成 to_tsquery 串：英文词 OR，口语虚词去掉，剩余 CJK 仍 AND。"""
    raw = (text_value or "").strip()
    if not raw:
        return ""
    seen: set[str] = set()
    latin: list[str] = []
    for tok in _LATIN_TOKEN.findall(raw):
        low = tok.lower()
        if low in _EN_STOP or low in seen:
            continue
        seen.add(low)
        latin.append(low)
    rest = _LATIN_TOKEN.sub(" ", raw)
    if lang != "en":
        for phrase in _ZH_NOISE_PHRASES:
            rest = rest.replace(phrase, " ")
    cjk: list[str] = []
    if lang == "ja":
        cjk = [c for c in rest if _JA_CHAR.match(c) and c not in _ZH_NOISE_CHARS]
    elif lang == "zh":
        cjk = [c for c in rest if "\u4e00" <= c <= "\u9fff" and c not in _ZH_NOISE_CHARS]
    latin_part = " | ".join(latin)
    cjk_part = " & ".join(cjk[:12])
    if latin_part and cjk_part:
        return f"({latin_part}) | ({cjk_part})"
    return latin_part or cjk_part


def _spaced_sql(col: str, lang: ChunkLang) -> str:
    base = f"coalesce({col}, '')"
    if lang == "en":
        return base
    if lang == "ja":
        return f"regexp_replace({base}, '([一-龥ぁ-ゖァ-ヺ])', '\\1 ', 'g')"
    return f"regexp_replace({base}, '([一-龥])', '\\1 ', 'g')"


def search_vector_sql_expr(lang: ChunkLang = DEFAULT_CHUNK_LANG) -> str:
    """按语言生成 search_vector 表达式（用于 UPDATE / 建表回填）。"""
    cfg = ts_config(lang)
    title = _spaced_sql("section_title", lang)
    path = _spaced_sql("section_path", lang)
    body = _spaced_sql("content", lang)
    return (
        f"setweight(to_tsvector('{cfg}', {title}), 'A') || "
        f"setweight(to_tsvector('{cfg}', {path}), 'A') || "
        f"setweight(to_tsvector('{cfg}', {body}), 'B')"
    )
