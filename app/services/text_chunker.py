import re
from dataclasses import dataclass

SECTION_SEP = re.compile(r"^=+\s*$", re.MULTILINE)
TITLE_PATTERN = re.compile(r"^【(.+?)】\s*$")
PUNCT_PATTERN = re.compile(r"([，。！？；：、,.!?;:])")

SMALL_PIECE_LEN = 20
CHUNK_LEN = 50


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
            content = "".join(
                line.strip()
                for line in blocks[index + 1].splitlines()
                if line.strip()
            )
            index += 2
        else:
            index += 1

        if title or path or content:
            sections.append(TextSection(title=title, path=path, content=content))

    return sections


def split_to_small_pieces(text: str, target_len: int = SMALL_PIECE_LEN) -> list[str]:
    """先按标点切分，过长片段再切到 target_len 左右。"""
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
        start = 0
        while start < len(piece):
            end = min(start + target_len, len(piece))
            pieces.append(piece[start:end])
            start = end

    return [p for p in pieces if p]


def merge_to_chunks(
    pieces: list[str],
    chunk_len: int = CHUNK_LEN,
) -> list[str]:
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
                start = 0
                while start < len(piece):
                    end = min(start + chunk_len, len(piece))
                    chunks.append(piece[start:end])
                    start = end
            continue

        if len(current) + len(piece) <= chunk_len + 5:
            current += piece
            continue

        chunks.append(current)
        if len(piece) <= chunk_len + 5:
            current = piece
        else:
            start = 0
            while start < len(piece):
                end = min(start + chunk_len, len(piece))
                chunks.append(piece[start:end])
                start = end
            current = ""

    if current:
        chunks.append(current)

    return chunks


def chunk_section(section: TextSection) -> list[TextChunk]:
    pieces = split_to_small_pieces(section.content)
    merged = merge_to_chunks(pieces)
    return [
        TextChunk(
            section_title=section.title,
            section_path=section.path,
            chunk_index=index,
            content=content,
        )
        for index, content in enumerate(merged)
    ]


def chunk_document(text: str) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for section in parse_sections(text):
        chunks.extend(chunk_section(section))
    return chunks
