"""全球 AI 发展趋势与智能演进数据自动更新服务。"""

from __future__ import annotations

import csv
import json
import logging
import ssl
import threading
import urllib.request
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "ai_trends"
CACHE_FILE = DATA_DIR / "ai_trends_stats.json"

LOCAL_TRENDS_CSV = BASE_DIR / "vue-manage-system-master" / "src" / "views" / "chart" / "global_ai_trends_2015_2026.csv"
LOCAL_INTEL_CSV = BASE_DIR / "vue-manage-system-master" / "src" / "views" / "chart" / "ai_intelligence_growth.csv"

# OWID：分国投资（CSET）+ AI 论文总量；智能演进口径不对齐，仍用本地
ONLINE_SOURCES = [
    (
        "https://ourworldindata.org/grapher/private-investment-in-artificial-intelligence-cset.csv"
        "?v=1&csvType=full&useColumnShortNames=false",
        "investment.csv",
    ),
    (
        "https://ourworldindata.org/grapher/annual-scholarly-publications-on-artificial-intelligence.csv"
        "?v=1&csvType=full&useColumnShortNames=false",
        "papers.csv",
    ),
]

INVESTMENT_VALUE_COL = "Estimated funding raised by privately held AI companies - Field: All"
PAPERS_VALUE_COL = "AI scholarly publications - Field: All"

# 本地国名 → OWID Entity（当前均为同名，保留映射以便扩展）
COUNTRY_ALIAS = {
    "United States": "United States",
    "United Kingdom": "United Kingdom",
    "United Arab Emirates": "United Arab Emirates",
    "South Korea": "South Korea",
}

_update_lock = threading.Lock()


class AiTrendsService:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_cached_stats(self) -> dict:
        """获取本地缓存的统计数据，若过期或不存在则异步触发更新。"""
        stats = self._read_cache()
        today_str = date.today().isoformat()

        if not stats or stats.get("updated_date") != today_str:
            self.trigger_async_update()

        if not stats:
            logger.info("AI Trends 缓存未就绪，同步解析本地备份...")
            stats = self._build_stats()
            if stats:
                self._write_cache(stats)
            else:
                stats = self._get_empty_fallback()

        return stats

    def trigger_async_update(self) -> None:
        """启动后台线程去下载并更新数据，不阻塞主线程。"""
        if not _update_lock.acquire(blocking=False):
            return

        def _task() -> None:
            try:
                self._update_all_data()
            except Exception as exc:
                logger.exception("更新 AI Trends 数据失败: %s", exc)
            finally:
                _update_lock.release()

        thread = threading.Thread(target=_task, name="ai-trends-updater", daemon=True)
        thread.start()

    def _read_cache(self) -> dict | None:
        if not CACHE_FILE.exists():
            return None
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("读取 AI Trends 缓存失败: %s", exc)
            return None

    def _write_cache(self, stats: dict) -> None:
        try:
            CACHE_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("写入 AI Trends 缓存文件失败: %s", exc)

    def _get_empty_fallback(self) -> dict:
        return {
            "status": "initializing",
            "updated_date": date.today().isoformat(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trends": [],
            "intelligence": [],
        }

    def _update_all_data(self) -> None:
        """下载 OWID CSV，并与本地宽表 merge 后写缓存。"""
        ctx = ssl._create_unverified_context()
        headers = {"User-Agent": "Mozilla/5.0 (compatible; cur_index-ai-trends/1.0)"}

        for url, filename in ONLINE_SOURCES:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
                    (DATA_DIR / filename).write_bytes(response.read())
                logger.info("成功下载: %s", filename)
            except Exception as exc:
                logger.warning("下载 %s 失败 (%s)，若有旧文件则继续 merge。", filename, exc)

        stats = self._build_stats()
        if stats:
            self._write_cache(stats)
            logger.info("AI Trends 缓存更新成功！")

    def _build_stats(self) -> dict | None:
        """本地宽表为底，用已下载的投资/论文覆盖可对齐字段。"""
        trends = self._parse_trends_csv(LOCAL_TRENDS_CSV)
        intelligence = self._parse_intelligence_csv(LOCAL_INTEL_CSV)
        if not trends and not intelligence:
            return None

        if trends:
            inv_map = self._parse_owid_kv(DATA_DIR / "investment.csv", INVESTMENT_VALUE_COL)
            papers_map = self._parse_owid_kv(DATA_DIR / "papers.csv", PAPERS_VALUE_COL)
            self._merge_trends(trends, inv_map, papers_map)

        return {
            "status": "success",
            "updated_date": date.today().isoformat(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trends": trends,
            "intelligence": intelligence,
        }

    def _merge_trends(
        self,
        trends: list[dict],
        inv_map: dict[tuple[str, int], float],
        papers_map: dict[tuple[str, int], float],
    ) -> None:
        """有 OWID 投资时只保留源数据；未命中置 null，避免本地演示年与真数混播。"""
        inv_hits = papers_hits = 0
        for row in trends:
            entity = COUNTRY_ALIAS.get(row["country"], row["country"])
            key = (entity, row["year"])
            if inv_map:
                if key in inv_map:
                    row["investmentBillionsUsd"] = round(inv_map[key] / 1e9, 2)
                    inv_hits += 1
                else:
                    row["investmentBillionsUsd"] = None
            if key in papers_map:
                row["publishedPapersThousands"] = round(papers_map[key] / 1000, 2)
                papers_hits += 1
        logger.info("OWID merge: investment=%s rows, papers=%s rows", inv_hits, papers_hits)

    def _parse_owid_kv(self, file_path: Path, value_col: str) -> dict[tuple[str, int], float]:
        """解析 OWID 长表 Entity/Year/值为 (entity, year) -> float。"""
        if not file_path.exists():
            return {}
        try:
            result: dict[tuple[str, int], float] = {}
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    entity = (row.get("Entity") or "").strip()
                    year_raw = row.get("Year")
                    raw_val = row.get(value_col)
                    if not entity or not year_raw or raw_val in (None, ""):
                        continue
                    try:
                        result[(entity, int(year_raw))] = float(raw_val)
                    except (TypeError, ValueError):
                        continue
            return result
        except Exception as exc:
            logger.error("解析 OWID CSV 失败 %s: %s", file_path.name, exc)
            return {}

    def _parse_trends_csv(self, file_path: Path) -> list[dict]:
        """解析全球 AI 趋势 CSV。"""
        if not file_path.exists():
            return []
        try:
            result = []
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    year_val = row.get("Year")
                    country_val = row.get("Country_Region")
                    if not year_val or not country_val:
                        continue
                    result.append({
                        "year": int(year_val),
                        "country": country_val,
                        "aiIndexScore": float(row.get("AI_Index_Score") or 0),
                        "investmentBillionsUsd": float(row.get("Investment_Billions_USD") or 0),
                        "publishedPapersThousands": float(row.get("Published_Papers_Thousands") or 0),
                        "aiTalentPoolThousands": float(row.get("AI_Talent_Pool_Thousands") or 0),
                        "primaryFocusArea": row.get("Primary_Focus_Area") or "",
                    })
            return result
        except Exception as exc:
            logger.error("解析全球 AI 趋势 CSV 失败: %s", exc)
            return []

    def _parse_intelligence_csv(self, file_path: Path) -> list[dict]:
        """解析 AI 智能演进 CSV。"""
        if not file_path.exists():
            return []
        try:
            result = []
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    year_val = row.get("Year")
                    if not year_val:
                        continue
                    result.append({
                        "year": int(year_val),
                        "readingComprehension": float(row.get("Reading_Comprehension") or 0),
                        "mathReasoning": float(row.get("Math_Reasoning") or 0),
                        "codeGeneration": float(row.get("Code_Generation") or 0),
                        "complexReasoningHumanityExam": float(row.get("Complex_Reasoning_Humanity_Exam") or 0),
                    })
            return result
        except Exception as exc:
            logger.error("解析 AI 智能演进 CSV 失败: %s", exc)
            return []


ai_trends_service = AiTrendsService()
