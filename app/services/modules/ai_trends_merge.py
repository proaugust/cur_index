"""OWID 投资/论文合并到底表，并追加底表之后的新年份。"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

COUNTRY_ALIAS = {
    "United States": "United States",
    "United Kingdom": "United Kingdom",
    "United Arab Emirates": "United Arab Emirates",
    "South Korea": "South Korea",
}


def _entity(country: str) -> str:
    return COUNTRY_ALIAS.get(country, country)


def append_new_owid_years(
    trends: list[dict],
    inv_map: dict[tuple[str, int], float],
    papers_map: dict[tuple[str, int], float],
) -> int:
    """底表最大年份之后，OWID 有跟踪国数据则追加行；指数/人才沿用该国最近一年。"""
    if not trends or (not inv_map and not papers_map):
        return 0
    max_year = max(row["year"] for row in trends)
    latest: dict[str, dict] = {}
    for row in trends:
        prev = latest.get(row["country"])
        if prev is None or row["year"] > prev["year"]:
            latest[row["country"]] = row
    tracked = {_entity(name) for name in latest}
    new_years = sorted({
        year
        for entity, year in (*inv_map, *papers_map)
        if year > max_year and entity in tracked
    })
    added = 0
    for year in new_years:
        for country, base in latest.items():
            entity = _entity(country)
            inv = inv_map.get((entity, year))
            papers = papers_map.get((entity, year))
            row = {
                **base,
                "year": year,
                "investmentBillionsUsd": round(inv / 1e9, 2) if inv is not None else None,
                "publishedPapersThousands": (
                    round(papers / 1000, 2)
                    if papers is not None
                    else base["publishedPapersThousands"]
                ),
            }
            trends.append(row)
            latest[country] = row
            added += 1
    return added


def merge_trends(
    trends: list[dict],
    inv_map: dict[tuple[str, int], float],
    papers_map: dict[tuple[str, int], float],
) -> None:
    inv_hits = papers_hits = 0
    for row in trends:
        key = (_entity(row["country"]), row["year"])
        if inv_map:
            if key in inv_map:
                row["investmentBillionsUsd"] = round(inv_map[key] / 1e9, 2)
                inv_hits += 1
            else:
                row["investmentBillionsUsd"] = None
        if key in papers_map:
            row["publishedPapersThousands"] = round(papers_map[key] / 1000, 2)
            papers_hits += 1
    added = append_new_owid_years(trends, inv_map, papers_map)
    logger.info(
        "OWID merge: investment=%s, papers=%s, appended=%s",
        inv_hits,
        papers_hits,
        added,
    )
