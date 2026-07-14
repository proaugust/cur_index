"""资料库导入 IO：本机文件夹 / ZIP 文本成员读取。"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException

_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}


def read_folder_texts(folder_path: str) -> list[tuple[str, str]]:
    root = Path(folder_path)
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"文件夹不存在: {folder_path}")

    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in _TEXT_SUFFIXES)
    if not files:
        raise HTTPException(status_code=400, detail="文件夹内没有 .md / .txt 文件")

    items: list[tuple[str, str]] = []
    for path in files:
        try:
            items.append((str(path.resolve()), path.read_text(encoding="utf-8-sig")))
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"文件编码必须是 UTF-8: {path}") from exc
    return items


def read_zip_texts(zip_bytes: bytes) -> list[tuple[str, str]]:
    """解析 zip（含子目录），返回 [(相对路径, 文本), ...]。"""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="无效的 ZIP 文件") from exc

    items: list[tuple[str, str]] = []
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.startswith("__MACOSX/") or "/__MACOSX/" in name:
                continue
            path = PurePosixPath(name)
            if ".." in path.parts or path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            try:
                text = zf.read(info).decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"文件编码必须是 UTF-8: {name}") from exc
            items.append((name, text))
    if not items:
        raise HTTPException(status_code=400, detail="ZIP 内没有 .md / .txt 文件")
    return sorted(items, key=lambda x: x[0])
