"""AI 资讯导航：链接目录 + 收藏（单表 ai_news_links）。"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app import models, schemas
from app.services.demo.ai_news_seed_data import DEFAULT_FAVORITE_CUSTOM, DEFAULT_FAVORITE_SLUGS, SYSTEM_PRESETS

logger = logging.getLogger(__name__)

_REGIONS = ("international", "domestic", "favorites")
_PALETTE = ["#409EFF", "#67C23A", "#E6A23C", "#F56C6C", "#909399", "#1E88E5", "#00B388", "#7B1FA2"]
_DOMESTIC_HOSTS = {
    urlparse(item["url"]).hostname.lower().replace("www.", "")
    for item in SYSTEM_PRESETS
    if item["region"] == "domestic"
}


def _hash_string(value: str) -> int:
    result = 0
    for char in value:
        result = (result * 31 + ord(char)) | 0
    return abs(result)


def _domain_to_color(host: str) -> str:
    return _PALETTE[_hash_string(host) % len(_PALETTE)]


def _domain_to_letter(host: str) -> str:
    clean = host.replace("www.", "")
    return clean[0].upper() if clean else "?"


def normalize_url(raw: str) -> str | None:
    trimmed = raw.strip()
    if not trimmed:
        return None
    try:
        url = urlparse(trimmed if "://" in trimmed else f"https://{trimmed}")
        if url.scheme not in {"http", "https"} or not url.netloc:
            return None
        return url.geturl()
    except ValueError:
        return None


def classify_region(url: str) -> str:
    host = urlparse(url).hostname.lower().replace("www.", "")
    if re.search(r"\.(cn|中国)$", host) or re.search(r"\.(com|net|org|gov|edu)\.cn$", host):
        return "domestic"
    if re.search(r"[\u4e00-\u9fff]", host):
        return "domestic"
    if any(host == root or host.endswith(f".{root}") for root in _DOMESTIC_HOSTS):
        return "domestic"
    if host in {"zhihu.com", "aiera.com.cn"} or host.endswith(".zhihu.com"):
        return "domestic"
    return "international"


def _load_system_links(db: Session) -> list[models.AiNewsLink]:
    return (
        db.query(models.AiNewsLink)
        .filter(models.AiNewsLink.user_id.is_(None))
        .order_by(models.AiNewsLink.region, models.AiNewsLink.sort_order, models.AiNewsLink.id)
        .all()
    )


def _load_user_links(db: Session, user_id: int) -> list[models.AiNewsLink]:
    return (
        db.query(models.AiNewsLink)
        .filter(models.AiNewsLink.user_id == user_id)
        .order_by(models.AiNewsLink.region, models.AiNewsLink.sort_order, models.AiNewsLink.id)
        .all()
    )


def _to_item(row: models.AiNewsLink, *, is_system: bool) -> schemas.AiNewsLinkItem:
    return schemas.AiNewsLinkItem(
        id=row.id,
        slug=row.slug,
        url=row.url,
        name=row.name,
        description=row.description or row.url,
        icon=row.icon,
        letter=row.letter,
        color=row.color,
        is_system=is_system,
    )


def _system_by_slug(system_rows: list[models.AiNewsLink]) -> dict[str, models.AiNewsLink]:
    return {row.slug: row for row in system_rows if row.slug}


def _build_column(
    region: str,
    system_rows: list[models.AiNewsLink],
    user_rows: list[models.AiNewsLink],
) -> list[schemas.AiNewsLinkItem]:
    system_map = _system_by_slug(system_rows)
    hidden_slugs = {row.slug for row in user_rows if row.slug and row.is_hidden}
    overrides = {
        row.slug: row
        for row in user_rows
        if row.slug and not row.is_hidden and row.region in {"international", "domestic"}
    }
    items: list[tuple[int, schemas.AiNewsLinkItem]] = []

    for row in user_rows:
        if row.slug or row.is_hidden or row.region != region:
            continue
        items.append((row.sort_order, _to_item(row, is_system=False)))

    for slug, system in system_map.items():
        if slug in hidden_slugs:
            continue
        override = overrides.get(slug)
        effective_region = override.region if override else system.region
        if effective_region != region:
            continue
        sort_order = override.sort_order if override else system.sort_order
        display = override or system
        items.append((sort_order, _to_item(display, is_system=True)))

    items.sort(key=lambda pair: (pair[0], pair[1].id))
    return [item for _, item in items]


def _build_favorites(
    system_rows: list[models.AiNewsLink],
    user_rows: list[models.AiNewsLink],
) -> list[schemas.AiNewsLinkItem]:
    system_map = _system_by_slug(system_rows)
    hidden_slugs = {row.slug for row in user_rows if row.slug and row.is_hidden}
    favorites = [row for row in user_rows if row.region == "favorites" and not row.is_hidden]
    favorites.sort(key=lambda row: (row.sort_order, row.id))
    items: list[schemas.AiNewsLinkItem] = []
    for row in favorites:
        if row.slug and row.slug in system_map and row.slug not in hidden_slugs:
            items.append(_to_item(row if row.name else system_map[row.slug], is_system=True))
        else:
            items.append(_to_item(row, is_system=bool(row.slug and row.slug in system_map)))
    return items


def _seed_default_favorites(db: Session, user_id: int, system_rows: list[models.AiNewsLink]) -> None:
    system_map = _system_by_slug(system_rows)
    sort_order = 10
    for slug in DEFAULT_FAVORITE_SLUGS:
        system = system_map.get(slug)
        if not system:
            continue
        db.add(
            models.AiNewsLink(
                user_id=user_id,
                slug=slug,
                url=system.url,
                name=system.name,
                description=system.description,
                region="favorites",
                sort_order=sort_order,
                icon=system.icon,
                letter=system.letter,
                color=system.color,
            )
        )
        sort_order += 10
    for custom in DEFAULT_FAVORITE_CUSTOM:
        url = normalize_url(custom["url"])
        if not url:
            continue
        host = urlparse(url).hostname or ""
        db.add(
            models.AiNewsLink(
                user_id=user_id,
                slug=None,
                url=url,
                name=custom["name"],
                description=url,
                region="favorites",
                sort_order=sort_order,
                icon="",
                letter=_domain_to_letter(host),
                color=_domain_to_color(host),
            )
        )
        sort_order += 10
    db.commit()


def get_board(db: Session, user_id: int) -> schemas.AiNewsBoardResponse:
    system_rows = _load_system_links(db)
    user_rows = _load_user_links(db, user_id)
    if not user_rows:
        _seed_default_favorites(db, user_id, system_rows)
        user_rows = _load_user_links(db, user_id)
    return schemas.AiNewsBoardResponse(
        international=_build_column("international", system_rows, user_rows),
        domestic=_build_column("domestic", system_rows, user_rows),
        favorites=_build_favorites(system_rows, user_rows),
    )


def _copy_row_fields(source: models.AiNewsLink) -> dict:
    return {
        "url": source.url,
        "name": source.name,
        "description": source.description,
        "icon": source.icon,
        "letter": source.letter,
        "color": source.color,
    }


def save_board(db: Session, user_id: int, payload: schemas.AiNewsBoardUpdate) -> schemas.AiNewsBoardResponse:
    system_rows = _load_system_links(db)
    system_map = _system_by_slug(system_rows)
    db.query(models.AiNewsLink).filter(models.AiNewsLink.user_id == user_id).delete()
    db.flush()

    visible_system_slugs: set[str] = set()

    def persist_column(region: str, items: list[schemas.AiNewsBoardEntry]) -> None:
        for index, entry in enumerate(items):
            sort_order = (index + 1) * 10
            if entry.slug and entry.slug in system_map:
                source = system_map[entry.slug]
                if region != "favorites":
                    visible_system_slugs.add(entry.slug)
                db.add(
                    models.AiNewsLink(
                        user_id=user_id,
                        slug=entry.slug,
                        region=region,
                        sort_order=sort_order,
                        **_copy_row_fields(source),
                    )
                )
                continue
            db.add(
                models.AiNewsLink(
                    user_id=user_id,
                    slug=entry.slug,
                    url=entry.url,
                    name=entry.name,
                    description=entry.description or entry.url,
                    region=region,
                    sort_order=sort_order,
                    icon=entry.icon,
                    letter=entry.letter,
                    color=entry.color,
                )
            )

    persist_column("international", payload.international)
    persist_column("domestic", payload.domestic)
    persist_column("favorites", payload.favorites)

    for slug, source in system_map.items():
        if slug in visible_system_slugs:
            continue
        db.add(
            models.AiNewsLink(
                user_id=user_id,
                slug=slug,
                region=source.region,
                sort_order=source.sort_order,
                is_hidden=True,
                **_copy_row_fields(source),
            )
        )

    db.commit()
    return get_board(db, user_id)


def create_custom_link(db: Session, user_id: int, url: str) -> schemas.AiNewsBoardResponse:
    normalized = normalize_url(url)
    if not normalized:
        raise ValueError("invalid_url")

    system_rows = _load_system_links(db)
    user_rows = _load_user_links(db, user_id)
    all_urls = {row.url for row in system_rows + user_rows}
    if normalized in all_urls:
        raise ValueError("duplicate_url")

    host = urlparse(normalized).hostname or ""
    region = classify_region(normalized)
    db.add(
        models.AiNewsLink(
            user_id=user_id,
            slug=None,
            url=normalized,
            name=host.replace("www.", ""),
            description=normalized,
            region=region,
            sort_order=0,
            icon="",
            letter=_domain_to_letter(host),
            color=_domain_to_color(host),
        )
    )
    db.commit()
    return get_board(db, user_id)
