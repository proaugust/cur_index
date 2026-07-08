import re
from dataclasses import dataclass

SECTION_SEP = re.compile(r"^=+\s*$", re.MULTILINE)
TITLE_PATTERN = re.compile(r"^【(.+?)】\s*$")
PUNCT_PATTERN = re.compile(r"([，。！？；：、,.!?;:])")
_PUNCT_CHARS = frozenset("，。！？；：、,.!?;:")
_BOUNDARY_SEARCH_WINDOW = 50

SMALL_PIECE_LEN = 10
CHUNK_LEN = 300
CHUNK_OVERLAP = 50

_FILLER_RUN = re.compile(r"[.\-_=*~#·]{5,}")
_DOT_RUN = re.compile(r"\.{5,}")
_ELLIPSIS_RUN = re.compile(r"…{3,}")
_WHITESPACE_RUN = re.compile(r"[ \t]{2,}")
_BLANK_LINE_RUN = re.compile(r"\n{3,}")


def _count_meaningful_chars(text: str) -> int:
    return sum(1 for ch in text if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")


def _meaningful_ratio(text: str) -> float:
    if not text:
        return 0.0
    return _count_meaningful_chars(text) / len(text)


def clean_section_content(text: str) -> str:
    """清洗 section 正文中的填充符号与纯噪声行（在 parse_sections 之后调用）。"""
    if not text:
        return ""

    cleaned = _FILLER_RUN.sub(" ", text)
    cleaned = _DOT_RUN.sub("...", cleaned)
    cleaned = _ELLIPSIS_RUN.sub("…", cleaned)
    cleaned = _WHITESPACE_RUN.sub(" ", cleaned)
    cleaned = _BLANK_LINE_RUN.sub("\n\n", cleaned)

    lines: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) > 5 and _count_meaningful_chars(stripped) < 3:
            continue
        lines.append(stripped)

    if lines:
        return "".join(lines)
    return cleaned.strip()


def is_meaningful_text(text: str, *, min_ratio: float = 0.3) -> bool:
    """判断片段是否含足够有效文字，用于过滤切块噪声。"""
    stripped = text.strip()
    if not stripped:
        return False

    meaningful = _count_meaningful_chars(stripped)
    if len(stripped) <= 10:
        return meaningful >= 1
    if meaningful < 3:
        return False
    return _meaningful_ratio(stripped) >= min_ratio


@dataclass
class TextSection:
    title: str
    path: str
    content: str


@dataclass
class TextChunk:
    section_title: str
    section_path: str
    chunk_index: int
    content: str


def parse_sections(text: str) -> list[TextSection]:
    """
    用 === 分隔符分段。

    文件结构:
        ====
        【标题】
        /path
        ====
        正文...
    """
    blocks = [block.strip() for block in SECTION_SEP.split(text)]
    sections: list[TextSection] = []
    index = 0

    while index < len(blocks):
        block = blocks[index]
        if not block:
            index += 1
            continue

        lines = [line.strip() for line in block.splitlines() if line.strip()]
        title = ""
        path = ""
        line_index = 0

        title_match = TITLE_PATTERN.match(lines[0]) if lines else None
        if title_match:
            title = title_match.group(1)
            line_index = 1
            if line_index < len(lines) and lines[line_index].startswith("/"):
                path = lines[line_index]
                line_index += 1

        if line_index < len(lines):
            content = "".join(lines[line_index:])
            sections.append(TextSection(title=title, path=path, content=content))
            index += 1
            continue

        content = ""
        if index + 1 < len(blocks):
            content = "".join(line.strip() for line in blocks[index + 1].splitlines() if line.strip())
            index += 2
        else:
            index += 1

        if title or path or content:
            sections.append(TextSection(title=title, path=path, content=content))

    return sections


def _find_split_end(text: str, start: int, max_len: int, *, search_window: int = _BOUNDARY_SEARCH_WINDOW) -> int:
    """在 max_len 附近向后找标点，找不到则硬切。"""
    if start >= len(text):
        return len(text)

    end = min(start + max_len, len(text))
    if end >= len(text):
        return end

    search_start = max(start + 1, end - search_window)
    for i in range(end - 1, search_start - 1, -1):
        if text[i] in _PUNCT_CHARS:
            return i + 1

    return end


def _split_by_length(text: str, max_len: int) -> list[str]:
    """按 max_len 切分，优先在标点处断开。"""
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = _find_split_end(text, start, max_len)
        if end <= start:
            end = min(start + max_len, len(text))
        parts.append(text[start:end])
        start = end
    return parts


def split_to_small_pieces(text: str, target_len: int = SMALL_PIECE_LEN) -> list[str]:
    """先按标点切分，过长片段再切到 target_len 左右（硬切前优先找标点）。"""
    if not text:
        return []

    parts = PUNCT_PATTERN.split(text)
    raw_pieces: list[str] = []
    buffer = ""

    for part in parts:
        if not part:
            continue
        if PUNCT_PATTERN.fullmatch(part):
            buffer += part
            if buffer.strip():
                raw_pieces.append(buffer.strip())
            buffer = ""
            continue
        buffer += part

    if buffer.strip():
        raw_pieces.append(buffer.strip())

    pieces: list[str] = []
    for piece in raw_pieces:
        if len(piece) <= target_len + 5:
            pieces.append(piece)
            continue
        pieces.extend(_split_by_length(piece, target_len))

    return [p for p in pieces if p]


def merge_to_chunks(pieces: list[str], chunk_len: int = CHUNK_LEN) -> list[str]:
    """将小块合并为 chunk_len 左右的 chunk。"""
    if not pieces:
        return []

    chunks: list[str] = []
    current = ""

    for piece in pieces:
        if not current:
            if len(piece) <= chunk_len + 5:
                current = piece
            else:
                chunks.extend(_split_by_length(piece, chunk_len))
            continue

        if len(current) + len(piece) <= chunk_len + 5:
            current += piece
            continue

        chunks.append(current)
        if len(piece) <= chunk_len + 5:
            current = piece
        else:
            chunks.extend(_split_by_length(piece, chunk_len))
            current = ""

    if current:
        chunks.append(current)

    return chunks


def apply_chunk_overlap(chunks: list[str], overlap: int) -> list[str]:
    """合并完成后，将上一块末尾 overlap 字符前缀拼接到当前块。"""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for chunk in chunks[1:]:
        prefix = chunks[len(result) - 1][-overlap:]
        result.append(prefix + chunk)
    return result


def chunk_section(
    section: TextSection,
    *,
    min_chunk_len: int = SMALL_PIECE_LEN,
    max_chunk_len: int = CHUNK_LEN,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[TextChunk]:
    content = clean_section_content(section.content)
    if not content:
        return []

    pieces = [p for p in split_to_small_pieces(content, target_len=min_chunk_len) if is_meaningful_text(p)]
    if not pieces:
        return []

    merged = [c for c in merge_to_chunks(pieces, chunk_len=max_chunk_len) if is_meaningful_text(c)]
    if not merged:
        return []

    merged = apply_chunk_overlap(merged, chunk_overlap)
    return [
        TextChunk(section_title=section.title, section_path=section.path, chunk_index=index, content=content) for index, content in enumerate(merged)
    ]


def chunk_document(
    text: str,
    *,
    min_chunk_len: int = SMALL_PIECE_LEN,
    max_chunk_len: int = CHUNK_LEN,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for section in parse_sections(text):
        chunks.extend(
            chunk_section(
                section,
                min_chunk_len=min_chunk_len,
                max_chunk_len=max_chunk_len,
                chunk_overlap=chunk_overlap,
            )
        )
    return chunks
