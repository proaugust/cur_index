"""Epoch AI CSV 解析：从本地 CSV 聚合看板统计。"""

from __future__ import annotations

import csv
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _classify_country(raw_country: str) -> str:
    if "United States" in raw_country:
        return "United States"
    if "China" in raw_country:
        return "China"
    if "United Kingdom" in raw_country:
        return "United Kingdom"
    if "France" in raw_country:
        return "France"
    if "Germany" in raw_country:
        return "Germany"
    if "Canada" in raw_country:
        return "Canada"
    if "Japan" in raw_country:
        return "Japan"
    return "Other"


def _classify_domain(raw_domain: str) -> str:
    if "Language" in raw_domain:
        return "Language"
    if "Vision" in raw_domain or "Image" in raw_domain:
        return "Vision"
    if "Multimodal" in raw_domain:
        return "Multimodal"
    if "Speech" in raw_domain or "Audio" in raw_domain:
        return "Speech/Audio"
    if "Robotics" in raw_domain:
        return "Robotics"
    return "Other"


def _parse_float(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def build_stats_from_csv(csv_path: Path) -> dict | None:
    """解析 Epoch CSV，返回看板用聚合 JSON；失败返回 None。"""
    if not csv_path.exists():
        return None

    try:
        with open(csv_path, mode="r", encoding="utf-8-sig", errors="ignore") as f:
            lines: list[str] = []
            for line in f:
                if line.startswith("Model,Domain,Task"):
                    lines.append(line)
                    break
            for line in f:
                lines.append(line)

            if not lines:
                return None

            reader = csv.DictReader(lines)
            total_count = 0
            notable_count = 0
            frontier_count = 0
            large_scale_count = 0
            yearly_countries: dict[int, dict[str, int]] = {}
            domains: dict[str, int] = {}
            open_weights = {"Yes": 0, "No": 0, "Unknown": 0}
            scatter_data: list[dict] = []
            latest_releases: list[dict] = []

            for row in reader:
                model_name = row.get("Model")
                pub_date = row.get("Publication date") or row.get("Publication Date", "")
                if not model_name or not pub_date:
                    continue

                total_count += 1
                is_notable = bool(row.get("Notability criteria"))
                if is_notable:
                    notable_count += 1

                is_frontier = row.get("Frontier model") in ("Yes", "True", "1")
                if is_frontier:
                    frontier_count += 1

                is_large = False
                comp_val = row.get("Training compute (FLOP)")
                if comp_val:
                    try:
                        if float(comp_val) >= 1e23:
                            is_large = True
                    except ValueError:
                        pass
                if not is_large and row.get("Possibly over 1e23 FLOP") in ("Yes", "True", "1"):
                    is_large = True
                if is_large:
                    large_scale_count += 1

                year_str = pub_date[:4]
                if year_str.isdigit() and 1950 <= int(year_str) <= 2026:
                    year = int(year_str)
                    country = _classify_country(row.get("Country (of organization)") or "Unknown")
                    if year not in yearly_countries:
                        yearly_countries[year] = {}
                    yearly_countries[year][country] = yearly_countries[year].get(country, 0) + 1

                main_domain = _classify_domain(row.get("Domain") or "Other")
                domains[main_domain] = domains.get(main_domain, 0) + 1

                weights_status = row.get("Open model weights?") or row.get("Open weights?")
                if weights_status in ("Yes", "True"):
                    open_weights["Yes"] += 1
                elif weights_status in ("No", "False"):
                    open_weights["No"] += 1
                else:
                    open_weights["Unknown"] += 1

                p_val = _parse_float(row.get("Parameters"))
                c_val = _parse_float(row.get("Training compute (FLOP)"))
                if p_val or c_val:
                    scatter_data.append(
                        {
                            "name": model_name,
                            "date": pub_date,
                            "org": row.get("Organization") or "Unknown",
                            "params": p_val,
                            "compute": c_val,
                            "domain": main_domain,
                            "is_frontier": is_frontier,
                            "is_notable": is_notable,
                        }
                    )

                latest_releases.append(
                    {
                        "name": model_name,
                        "org": row.get("Organization") or "Unknown",
                        "date": pub_date,
                        "domain": main_domain,
                        "parameters": row.get("Parameters") or "Unknown",
                        "accessibility": row.get("Model accessibility") or "Unknown",
                    }
                )

            scatter_data.sort(key=lambda x: x["date"], reverse=True)
            latest_releases.sort(key=lambda x: x["date"], reverse=True)
            formatted_yearly = [
                {"year": yr, "countries": yearly_countries[yr]}
                for yr in sorted(yearly_countries.keys())
            ]

            return {
                "status": "success",
                "updated_date": date.today().isoformat(),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "counts": {
                    "all_models": total_count,
                    "notable_models": notable_count,
                    "frontier_models": frontier_count,
                    "large_scale_models": large_scale_count,
                },
                "yearly_countries": formatted_yearly,
                "domains": domains,
                "open_weights": open_weights,
                "scatter_data": scatter_data[:150],
                "latest_releases": latest_releases[:15],
            }
    except Exception as exc:
        logger.exception("解析 Epoch AI CSV 失败: %s", exc)
        return None
