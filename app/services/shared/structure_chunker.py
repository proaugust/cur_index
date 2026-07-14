"""结构感知切分：Markdown 标题分区 + 天然段落合并。"""

from __future__ import annotations

import re

from app.services.shared.text_chunker import (
    CHUNK_OVERLAP,
    TextChunk,
    TextSection,
    _find_split_end,
    apply_chunk_overlap,
    is_meaningful_text,
)

MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FILLER_RUN = re.compile(r"[.\-_=*~#·]{5,}")
_DOT_RUN = re.compile(r"\.{5,}")
_WHITESPACE_RUN = re.compile(r"[ \t]{2,}")

DEFAULT_MIN_CHUNK = 300
DEFAULT_MAX_CHUNK = 500
DEFAULT_OVERLAP = 80


def clean_paragraph_text(text: str) -> str:
    """清洗噪声，保留段落换行。"""
    if not text:
        return ""
    cleaned = _FILLER_RUN.sub(" ", text)
    cleaned = _DOT_RUN.sub("...", cleaned)
    cleaned = _WHITESPACE_RUN.sub(" ", cleaned)
    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        lines.append(stripped)
    # 压缩连续空行，保留分段语义
    paras: list[str] = []
    buf: list[str] = []
    for line in lines:
        if not line:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        paras.append(" ".join(buf))
    return "\n\n".join(paras)


def parse_markdown_sections(text: str) -> list[TextSection]:
    """按 ATGx Markdown 标题切分为 TextSection；无标题则整篇为一段。"""
    if not text or not text.strip():
        return []

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sections: list[TextSection] = []
    stack: list[tuple[int, str]] = []
    current_title = ""
    current_path = ""
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if content or current_title:
            sections.append(TextSection(title=current_title, path=current_path, content=content))

    for line in lines:
        match = MD_HEADING.match(line.strip())
        if not match:
            body.append(line)
            continue
        flush()
        body = []
        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        current_title = title
        current_path = "/" + "/".join(t for _, t in stack)

    flush()
    if not sections:
        sections.append(TextSection(title="", path="", content=text.strip()))
    return sections


def split_paragraphs(text: str) -> list[str]:
    cleaned = clean_paragraph_text(text)
    if not cleaned:
        return []
    return [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]


def _split_long_paragraph(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len + 20:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = _find_split_end(text, start, max_len)
        if end <= start:
            end = min(start + max_len, len(text))
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]


def merge_paragraphs_to_chunks(
    paragraphs: list[str],
    *,
    min_chunk_len: int,
    max_chunk_len: int,
) -> list[str]:
    """短段落合并至不低于 min；超 max 时在段落边界或标点处断开。"""
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        pieces = _split_long_paragraph(para, max_chunk_len) if len(para) > max_chunk_len + 20 else [para]
        for piece in pieces:
            if not current:
                current = piece
                continue
            joined_len = len(current) + 1 + len(piece)
            if joined_len <= max_chunk_len:
                current = f"{current}\n\n{piece}"
                continue
            if len(current) < min_chunk_len and joined_len <= max_chunk_len + 50:
                current = f"{current}\n\n{piece}"
                continue
            chunks.append(current)
            current = piece

    if current:
        # 末块过短则并入上一块（未超硬上限时）
        if chunks and len(current) < min_chunk_len and len(chunks[-1]) + 1 + len(current) <= max_chunk_len + 80:
            chunks[-1] = f"{chunks[-1]}\n\n{current}"
        else:
            chunks.append(current)
    return chunks


def chunk_section_structure(
    section: TextSection,
    *,
    min_chunk_len: int = DEFAULT_MIN_CHUNK,
    max_chunk_len: int = DEFAULT_MAX_CHUNK,
    chunk_overlap: int = DEFAULT_OVERLAP,
) -> list[TextChunk]:
    paragraphs = [p for p in split_paragraphs(section.content) if is_meaningful_text(p)]
    if not paragraphs:
        return []
    merged = [
        c
        for c in merge_paragraphs_to_chunks(paragraphs, min_chunk_len=min_chunk_len, max_chunk_len=max_chunk_len)
        if is_meaningful_text(c)
    ]
    if not merged:
        return []
    merged = apply_chunk_overlap(merged, chunk_overlap)
    return [
        TextChunk(
            section_title=section.title,
            section_path=section.path,
            chunk_index=index,
            content=content,
        )
        for index, content in enumerate(merged)
    ]


def chunk_document_structure(
    text: str,
    *,
    min_chunk_len: int = DEFAULT_MIN_CHUNK,
    max_chunk_len: int = DEFAULT_MAX_CHUNK,
    chunk_overlap: int = DEFAULT_OVERLAP,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    global_index = 0
    for section in parse_markdown_sections(text):
        section_chunks = chunk_section_structure(
            section,
            min_chunk_len=min_chunk_len,
            max_chunk_len=max_chunk_len,
            chunk_overlap=chunk_overlap,
        )
        for item in section_chunks:
            chunks.append(
                TextChunk(
                    section_title=item.section_title,
                    section_path=item.section_path,
                    chunk_index=global_index,
                    content=item.content,
                )
            )
            global_index += 1
    return chunks
