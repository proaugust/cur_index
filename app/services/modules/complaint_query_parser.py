import json
import logging
import re
from calendar import monthrange
from datetime import date, datetime

from fastapi import HTTPException

from app.core.config import settings
from app.services.modules.complaint_categories import CATEGORY_SEEDS
from app.services.modules.complaint_generator import _ADDRESSES as SAMPLE_ADDRESSES
from app.services.shared.llm import chat_completion

logger = logging.getLogger(__name__)

_CATEGORY_NAMES = list(CATEGORY_SEEDS.keys())

_PARSE_SYSTEM_TEMPLATE = """你是电信投诉查询解析助手。将用户的自然语言转为 JSON 查询参数，供后端安全聚合统计使用。

今天日期：{today}

标准投诉类型（category_name 只能从中选一或 null）：
{categories}

标准地区（address 只能填列表中的名称或 null）：
{addresses}

只输出 JSON，字段如下：
{{
  "intent": "stats" 或 "samples",
  "time_from": "YYYY-MM-DD" 或 null,
  "time_to": "YYYY-MM-DD" 或 null,
  "category_name": string 或 null,
  "address": string 或 null,
  "group_by": "address" 或 "category" 或 "day" 或 null,
  "rank": "max" 或 "min",
  "limit": 1-20
}}

规则：
1. 问「哪个区/地区/哪个地方」最多/最少 → intent=stats, group_by=address
2. 问「哪种/哪类/什么类型」最多/最少 → intent=stats, group_by=category
3. 问「哪天/按天」最多/最少 → intent=stats, group_by=day
4. 问「列出/查看/显示/查询…明细/记录/样本」→ intent=samples, group_by=null
5. 「N月」「上个月」「本月」须结合今天日期换算 time_from/time_to（含起止当天）
6. 库内投诉数据时间范围为 {data_range}。用户说「本月」或点击示例中的月份时，优先使用库内有数据的月份（取最晚日期所在月）；用户明确指定且不在范围内的月份仍按指定月份解析
7. 已指定某区/某类作为条件时填 filters，不要与 group_by 维度冲突（例如已指定新宿区则 group_by 不能是 address）
8. 最多/最高/最大 → rank=max；最少/最低/最小 → rank=min
9. limit 默认 5；仅问「哪个」时可用 1
"""


def _format_data_range(data_time_from: date | None, data_time_to: date | None) -> str:
    if data_time_from and data_time_to:
        return f"{data_time_from.isoformat()} 至 {data_time_to.isoformat()}"
    if data_time_to:
        return f"至 {data_time_to.isoformat()}"
    if data_time_from:
        return f"自 {data_time_from.isoformat()}"
    return "未知（按今天日期推断）"


def _build_system_prompt(
    *,
    data_time_from: date | None = None,
    data_time_to: date | None = None,
) -> str:
    return _PARSE_SYSTEM_TEMPLATE.format(
        today=date.today().isoformat(),
        categories="、".join(_CATEGORY_NAMES),
        addresses="、".join(SAMPLE_ADDRESSES),
        data_range=_format_data_range(data_time_from, data_time_to),
    )


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _parse_iso_date(value: object) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _match_category_name(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text in _CATEGORY_NAMES:
        return text
    for name in _CATEGORY_NAMES:
        if name in text or text in name:
            return name
    aliases = {
        "客服": "客服与渠道体验",
        "账单": "资费与账单争议",
        "资费": "资费与账单争议",
        "网络": "网络与信号质量",
        "信号": "网络与信号质量",
        "售后": "售后与维保服务",
        "硬件": "硬件产品质量",
        "账户": "账户安全与隐私",
        "安全": "账户安全与隐私",
        "营销": "营销与骚扰",
        "骚扰": "营销与骚扰",
        "套餐": "套餐变更与销户",
        "销户": "套餐变更与销户",
    }
    for key, name in aliases.items():
        if key in text:
            return name
    return None


def _apply_month_from_question(
    question: str,
    time_from: date | None,
    time_to: date | None,
    *,
    data_time_from: date | None,
    data_time_to: date | None,
) -> tuple[date | None, date | None]:
    match = re.search(r"(\d{1,2})月", question)
    if not match or not data_time_to:
        return time_from, time_to
    month = int(match.group(1))
    if month < 1 or month > 12:
        return time_from, time_to

    year = data_time_to.year
    if data_time_from and month < data_time_from.month:
        year = data_time_from.year
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    if data_time_from:
        start = max(start, data_time_from)
    if data_time_to:
        end = min(end, data_time_to)
    if start > end:
        return time_from, time_to
    return start, end


def _match_address(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for address in SAMPLE_ADDRESSES:
        if address == text or address in text or text in address:
            return address
    return text[:100]


def parse_complaint_query(
    question: str,
    *,
    data_time_from: date | None = None,
    data_time_to: date | None = None,
):
    from app import schemas

    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，无法解析自然语言查询")

    user_prompt = f"用户查询：\n{question.strip()}"
    try:
        raw = chat_completion(
            _build_system_prompt(data_time_from=data_time_from, data_time_to=data_time_to),
            user_prompt,
            temperature=0.1,
            json_mode=True,
            caller="complaint.stats_parse",
        )
        parsed = _parse_json(raw)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("投诉查询 LLM 解析失败", exc_info=True)
        raise HTTPException(status_code=400, detail="无法理解该查询，请参考示例重新描述") from exc

    intent = str(parsed.get("intent", "stats")).strip().lower()
    if intent not in {"stats", "samples"}:
        intent = "stats"

    time_from = _parse_iso_date(parsed.get("time_from"))
    time_to = _parse_iso_date(parsed.get("time_to"))
    time_from, time_to = _apply_month_from_question(
        question.strip(),
        time_from,
        time_to,
        data_time_from=data_time_from,
        data_time_to=data_time_to,
    )
    if time_from and time_to and time_from > time_to:
        time_from, time_to = time_to, time_from

    category_name = _match_category_name(parsed.get("category_name"))
    address = _match_address(parsed.get("address"))

    group_by = parsed.get("group_by")
    if group_by is not None:
        group_by = str(group_by).strip().lower()
        if group_by not in {"address", "category", "day"}:
            group_by = None

    rank = str(parsed.get("rank", "max")).strip().lower()
    if rank not in {"max", "min"}:
        rank = "max"

    try:
        limit = int(parsed.get("limit", 5))
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 20))

    if intent == "stats" and group_by is None:
        if category_name and not address:
            group_by = "address"
        elif address and not category_name:
            group_by = "category"
        else:
            group_by = "address"

    if intent == "stats" and group_by == "address" and address:
        raise HTTPException(status_code=400, detail="已指定地区时无法再问「哪个地区最多/最少」，请改问类型或换地区条件")
    if intent == "stats" and group_by == "category" and category_name:
        raise HTTPException(status_code=400, detail="已指定投诉类型时无法再问「哪种类型最多/最少」，请改问地区或换类型条件")

    filters = schemas.ComplaintStatsFilters(
        time_from=time_from,
        time_to=time_to,
        category_name=category_name,
        address=address,
    )
    return schemas.ComplaintStatsParsedQuery(
        intent=intent,
        filters=filters,
        group_by=group_by,
        rank=rank,
        limit=limit,
        original_question=question.strip(),
    )
