"""Epoch AI 全量大模型数据：Redis + 种子文件缓存，每日异步更新。"""

from __future__ import annotations

import json
import logging
import ssl
import threading
import urllib.request
from datetime import date, datetime
from pathlib import Path

from app.core.config import settings
from app.services.modules.epoch_csv import build_stats_from_csv
from app.services.shared.redis_client import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "epoch_ai"
CACHE_FILE = DATA_DIR / "epoch_ai_stats.json"
LOCAL_CSV = DATA_DIR / "all_ai_models.csv"
ONLINE_CSV_URL = "https://epoch.ai/data/all_ai_models.csv"
REDIS_KEY = "cache:epoch_ai:stats"

_update_lock = threading.Lock()
_memory_stats: dict | None = None
# 种子 json 仅在 Redis/内存皆空时回填一次，避免请求反复读盘
_seed_backfill_attempted = False


class EpochAiService:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_cached_stats(self) -> dict:
        """读路径：Redis → 内存 → 种子 json（仅一次，回填 Redis）。请求不读 CSV。

        写路径：下载解析后经 `_write_cache` 写 Redis + 种子 + 内存。
        """
        stats = self._read_cache()
        if not stats or stats.get("updated_date") != date.today().isoformat():
            self.trigger_async_update()

        if stats:
            return stats
        if _memory_stats and _memory_stats.get("status") == "success":
            return _memory_stats
        return self._get_empty_fallback()

    def trigger_async_update(self) -> None:
        if not _update_lock.acquire(blocking=False):
            return

        def _task() -> None:
            try:
                self._update_all_data()
            except Exception as exc:
                logger.exception("更新 Epoch AI 数据失败: %s", exc)
            finally:
                _update_lock.release()

        threading.Thread(target=_task, name="epoch-ai-updater", daemon=True).start()

    def _read_cache(self) -> dict | None:
        global _memory_stats, _seed_backfill_attempted

        if settings.redis_enabled:
            cached = cache_get_json(REDIS_KEY)
            if isinstance(cached, dict) and cached.get("status") == "success":
                _memory_stats = cached
                return cached

        if _memory_stats and _memory_stats.get("status") == "success":
            self._write_redis(_memory_stats)
            return _memory_stats

        if _seed_backfill_attempted:
            return None
        _seed_backfill_attempted = True

        if not CACHE_FILE.exists():
            return None
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("status") == "success":
                _memory_stats = data
                self._write_redis(data)
                return data
        except Exception as exc:
            logger.warning("读取 Epoch AI 种子/缓存失败: %s", exc)
        return None

    def _write_redis(self, stats: dict) -> None:
        if not settings.redis_enabled:
            return
        cache_set_json(REDIS_KEY, stats, ttl=settings.epoch_ai_cache_ttl)

    def _write_cache(self, stats: dict) -> None:
        """更新完成后：内存 + Redis + 本地种子一并更新。"""
        global _memory_stats
        _memory_stats = stats
        self._write_redis(stats)
        try:
            CACHE_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("写入 Epoch AI 本地缓存失败（容器只读时属预期）: %s", exc)

    def _cleanup_runtime_csv(self) -> None:
        try:
            if LOCAL_CSV.exists():
                LOCAL_CSV.unlink()
        except Exception as exc:
            logger.warning("删除 Epoch AI 运行时 CSV 失败: %s", exc)

    def _get_empty_fallback(self) -> dict:
        return {
            "status": "initializing",
            "updated_date": "",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "counts": {
                "all_models": 0,
                "notable_models": 0,
                "frontier_models": 0,
                "large_scale_models": 0,
            },
            "yearly_countries": [],
            "domains": {},
            "open_weights": {"Yes": 0, "No": 0, "Unknown": 0},
            "scatter_data": [],
            "latest_releases": [],
        }

    def _update_all_data(self) -> None:
        logger.info("开始下载最新的 Epoch AI 数据: %s", ONLINE_CSV_URL)
        ctx = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(ONLINE_CSV_URL, timeout=60, context=ctx) as response:
                LOCAL_CSV.write_bytes(response.read())
            logger.info("Epoch AI CSV 下载成功: %s", LOCAL_CSV)
        except Exception as exc:
            logger.warning("从官网下载 CSV 失败 (%s)，放弃本次更新。", exc)
            return

        stats = build_stats_from_csv(LOCAL_CSV)
        if stats:
            self._write_cache(stats)
            logger.info("Epoch AI 缓存聚合数据更新成功")
        else:
            logger.error("无法构建 Epoch AI 数据缓存")
        self._cleanup_runtime_csv()


epoch_service = EpochAiService()
