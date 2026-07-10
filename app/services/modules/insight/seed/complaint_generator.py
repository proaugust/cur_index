"""投诉字段造数：写入 insight_complaint_sample。"""

import random
from datetime import datetime, timedelta

from app.services.modules.insight.seed.complaint_templates import render_complaint_text

_RANDOM = random.Random(77)
_COMPLAINT_SEQ = 0


def reset_complaint_seq(start: int = 0) -> None:
    global _COMPLAINT_SEQ
    _COMPLAINT_SEQ = start


def _next_complaint_id(dt: datetime) -> str:
    global _COMPLAINT_SEQ
    _COMPLAINT_SEQ += 1
    return f"C{dt.strftime('%Y%m%d')}{_COMPLAINT_SEQ:05d}"


def build_complaint_row(pair: dict, user: dict) -> dict:
    sample_time = datetime.utcnow() - timedelta(days=_RANDOM.randint(0, 365), hours=_RANDOM.randint(0, 23))
    customer_ctx = {
        "customer_id": user["user_id"],
        "province": user.get("_province", user.get("region_l1", user["region"].split("·")[0])),
        "city": user.get("_city", user.get("region_l2", user["region"].split("·")[-1])),
        "package_type": user["plan_id"],
        "monthly_fee": user["monthly_fee"],
        "vip_level": user["vip_level"],
        "network_type": user.get("_network_type", "5G"),
        "device": user.get("_device", "iPhone 15"),
    }
    return {
        "complaint_id": _next_complaint_id(sample_time),
        "user_id": user["user_id"],
        "sample_time": sample_time,
        "record_date": sample_time.date(),
        "complaint_type": pair["main_category"],
        "sub_category": pair["sub_category"],
        "raw_text": render_complaint_text(
            {"complaint_type": pair["main_category"], "sub_type": pair["sub_category"]},
            customer_ctx,
        ),
    }


def build_preview_row(pair: dict, user: dict) -> dict:
    customer_ctx = {
        "province": user.get("_province", "东京都"),
        "city": user.get("_city", "千代田区"),
        "package_type": user.get("plan_id", "199元套餐"),
        "monthly_fee": user.get("monthly_fee", 199),
        "vip_level": user.get("vip_level", "普通"),
        "network_type": user.get("_network_type", "5G"),
        "device": user.get("_device", "iPhone 15"),
    }
    return {
        "main_category": pair["main_category"],
        "sub_category": pair["sub_category"],
        "raw_text": render_complaint_text(
            {"complaint_type": pair["main_category"], "sub_type": pair["sub_category"]},
            customer_ctx,
        ),
    }
