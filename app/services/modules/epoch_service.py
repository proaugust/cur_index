"""Epoch AI 全量大模型数据解析与每日自动更新服务。"""

from __future__ import annotations

import csv
import json
import logging
import os
import ssl
import threading
import urllib.request
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 数据与缓存文件目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "epoch_ai"
CACHE_FILE = DATA_DIR / "epoch_ai_stats.json"

# 本地上传的备份样本路径
UPLOADED_BACKUP_CSV = Path("C:/Users/proau/.cursor/projects/d-code-py-demo-cur-index/uploads/all_ai_models-0.csv")

ONLINE_CSV_URL = "https://epoch.ai/data/all_ai_models.csv"

_update_lock = threading.Lock()


class EpochAiService:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_cached_stats(self) -> dict:
        """获取本地预计算的缓存统计数据，若过期或不存在则异步触发更新。"""
        stats = self._read_cache()
        today_str = date.today().isoformat()

        # 如果没有缓存，或者缓存不是今天的，就触发后台异步下载更新
        if not stats or stats.get("updated_date") != today_str:
            self.trigger_async_update()

        # 如果连历史缓存都没有，我们尝试先同步解析一次本地备份
        if not stats:
            logger.info("Epoch AI 缓存未就绪，尝试同步解析本地备份...")
            stats = self._build_from_file()
            if stats:
                # 写入初始缓存
                self._write_cache(stats)
            else:
                # 最后的兜底初始数据
                stats = self._get_empty_fallback()

        return stats

    def trigger_async_update(self) -> None:
        """启动后台线程去下载并更新数据，不阻塞 HTTP 启动与主线程响应。"""
        if not _update_lock.acquire(blocking=False):
            return

        def _task() -> None:
            try:
                self._update_all_data()
            except Exception as exc:
                logger.exception("更新 Epoch AI 数据失败: %s", exc)
            finally:
                _update_lock.release()

        thread = threading.Thread(target=_task, name="epoch-ai-updater", daemon=True)
        thread.start()

    def _read_cache(self) -> dict | None:
        if not CACHE_FILE.exists():
            return None
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("读取 Epoch AI 缓存失败: %s", exc)
            return None

    def _write_cache(self, stats: dict) -> None:
        try:
            CACHE_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("写入 Epoch AI 缓存文件失败: %s", exc)

    def _get_empty_fallback(self) -> dict:
        return {
            "status": "initializing",
            "updated_date": date.today().isoformat(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "counts": {"all_models": 0, "notable_models": 0, "frontier_models": 0, "large_scale_models": 0},
            "yearly_countries": {},
            "domains": {},
            "open_weights": {"Yes": 0, "No": 0, "Unknown": 0},
            "scatter_data": [],
            "latest_releases": []
        }

    def _update_all_data(self) -> None:
        """下载官方最新的 CSV 并进行聚合解析。"""
        local_csv = DATA_DIR / "all_ai_models.csv"
        logger.info("开始下载最新的 Epoch AI 数据: %s", ONLINE_CSV_URL)

        # 忽略 SSL 证书验证，避免企业/本地代理网关拦截报错
        ctx = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(ONLINE_CSV_URL, timeout=15, context=ctx) as response:
                local_csv.write_bytes(response.read())
            logger.info("Epoch AI 数据下载成功，写入至: %s", local_csv)
        except Exception as exc:
            logger.warning("从官网下载 CSV 失败 (%s)。将尝试使用已有文件或本地备份。", exc)

        stats = self._build_from_file()
        if stats:
            self._write_cache(stats)
            logger.info("Epoch AI 缓存聚合数据更新成功！")
        else:
            logger.error("无法构建 Epoch AI 数据缓存（本地和线上文件均不可用）")

    def _build_from_file(self) -> dict | None:
        """从本地下载的 CSV 或备份的 CSV 文件解析大模型指标并进行降维聚合。"""
        local_csv = DATA_DIR / "all_ai_models.csv"
        if not local_csv.exists():
            if UPLOADED_BACKUP_CSV.exists():
                local_csv = UPLOADED_BACKUP_CSV
            else:
                return None

        try:
            with open(local_csv, mode="r", encoding="utf-8-sig", errors="ignore") as f:
                lines = []
                # 略过开头的非 CSV 描述行（前几行可能存在 Source URL 或标题）
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

                # 聚合指标
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

                    # 显著模型
                    is_notable = bool(row.get("Notability criteria"))
                    if is_notable:
                        notable_count += 1

                    # 前沿模型
                    is_frontier = row.get("Frontier model") in ("Yes", "True", "1")
                    if is_frontier:
                        frontier_count += 1

                    # 超大规模模型 (1e23 FLOPs)
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

                    # 按年份与国家分布
                    year_str = pub_date[:4]
                    if year_str.isdigit() and 1950 <= int(year_str) <= 2026:
                        year = int(year_str)
                        raw_country = row.get("Country (of organization)") or "Unknown"
                        
                        # 国家名称精简化归类
                        if "United States" in raw_country:
                            country = "United States"
                        elif "China" in raw_country:
                            country = "China"
                        elif "United Kingdom" in raw_country:
                            country = "United Kingdom"
                        elif "France" in raw_country:
                            country = "France"
                        elif "Germany" in raw_country:
                            country = "Germany"
                        elif "Canada" in raw_country:
                            country = "Canada"
                        elif "Japan" in raw_country:
                            country = "Japan"
                        else:
                            country = "Other"

                        if year not in yearly_countries:
                            yearly_countries[year] = {}
                        yearly_countries[year][country] = yearly_countries[year].get(country, 0) + 1

                    # 技术路线分类 (Domain)
                    raw_domain = row.get("Domain") or "Other"
                    if "Language" in raw_domain:
                        main_domain = "Language"
                    elif "Vision" in raw_domain or "Image" in raw_domain:
                        main_domain = "Vision"
                    elif "Multimodal" in raw_domain:
                        main_domain = "Multimodal"
                    elif "Speech" in raw_domain or "Audio" in raw_domain:
                        main_domain = "Speech/Audio"
                    elif "Robotics" in raw_domain:
                        main_domain = "Robotics"
                    else:
                        main_domain = "Other"
                    domains[main_domain] = domains.get(main_domain, 0) + 1

                    # 开源占比
                    weights_status = row.get("Open model weights?") or row.get("Open weights?")
                    if weights_status in ("Yes", "True"):
                        open_weights["Yes"] += 1
                    elif weights_status in ("No", "False"):
                        open_weights["No"] += 1
                    else:
                        open_weights["Unknown"] += 1

                    # 精简散点图点：有参数或算力的才记录
                    params = row.get("Parameters")
                    compute = row.get("Training compute (FLOP)")
                    p_val, c_val = None, None
                    if params:
                        try:
                            p_val = float(params)
                        except ValueError:
                            pass
                    if compute:
                        try:
                            c_val = float(compute)
                        except ValueError:
                            pass

                    if p_val or c_val:
                        scatter_data.append({
                            "name": model_name,
                            "date": pub_date,
                            "org": row.get("Organization") or "Unknown",
                            "params": p_val,
                            "compute": c_val,
                            "domain": main_domain,
                            "is_frontier": is_frontier,
                            "is_notable": is_notable
                        })

                    # 最新发布的 15 个模型
                    latest_releases.append({
                        "name": model_name,
                        "org": row.get("Organization") or "Unknown",
                        "date": pub_date,
                        "domain": main_domain,
                        "parameters": params or "Unknown",
                        "accessibility": row.get("Model accessibility") or "Unknown"
                    })

                # 数据后处理与过滤
                # 1. 散点图限制 150 个，避免前端渲染过载，优先选用最新及知名模型
                scatter_data.sort(key=lambda x: x["date"], reverse=True)
                sampled_scatter = scatter_data[:150]

                # 2. 最新发布大模型
                latest_releases.sort(key=lambda x: x["date"], reverse=True)
                sampled_releases = latest_releases[:15]

                # 3. 补齐年份与排序
                sorted_years = sorted(yearly_countries.keys())
                formatted_yearly = []
                for yr in sorted_years:
                    formatted_yearly.append({
                        "year": yr,
                        "countries": yearly_countries[yr]
                    })

                return {
                    "status": "success",
                    "updated_date": date.today().isoformat(),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "counts": {
                        "all_models": total_count,
                        "notable_models": notable_count,
                        "frontier_models": frontier_count,
                        "large_scale_models": large_scale_count
                    },
                    "yearly_countries": formatted_yearly,
                    "domains": domains,
                    "open_weights": open_weights,
                    "scatter_data": sampled_scatter,
                    "latest_releases": sampled_releases
                }

        except Exception as exc:
            logger.exception("解析 Epoch AI CSV 文件发生错误: %s", exc)
            return None


epoch_service = EpochAiService()
