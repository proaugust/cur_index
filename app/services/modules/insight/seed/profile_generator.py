"""用户画像造数：insight_user_profile 静态字段。"""

import random
from datetime import date, timedelta

from app.services.modules.insight.constants import (
    DEVICES,
    GIVEN_NAMES,
    NETWORK_TYPES,
    PLAN_FEES,
    REGION_CITIES,
    SURNAMES,
    age_to_group,
)

_RANDOM = random.Random(42)

_VIP_WEIGHTS = [("普通", 55), ("银卡", 25), ("金卡", 15), ("钻石", 5)]
_USER_SEQ = 0


def _next_user_id() -> str:
    global _USER_SEQ
    _USER_SEQ += 1
    return f"{10000000 + _USER_SEQ:08d}"


def reset_user_seq(start: int = 0) -> None:
    global _USER_SEQ
    _USER_SEQ = start


def _weighted_vip() -> str:
    total = sum(weight for _, weight in _VIP_WEIGHTS)
    pick = _RANDOM.randint(1, total)
    acc = 0
    for label, weight in _VIP_WEIGHTS:
        acc += weight
        if pick <= acc:
            return label
    return "普通"


def _pick_region() -> tuple[str, str]:
    province = _RANDOM.choice(list(REGION_CITIES.keys()))
    city = _RANDOM.choice(REGION_CITIES[province])
    return province, city


def _pick_plan(vip_level: str) -> tuple[str, float]:
    plans = list(PLAN_FEES.items())
    if vip_level == "钻石":
        plans = plans[-3:]
    elif vip_level == "金卡":
        plans = plans[2:6]
    elif vip_level == "银卡":
        plans = plans[1:5]
    else:
        plans = plans[:4]
    name, fee = _RANDOM.choice(plans)
    jitter = _RANDOM.choice([0, 0, 5, 10, -5])
    return name, max(59.0, fee + jitter)


def generate_profile_row() -> dict:
    province, city = _pick_region()
    age = _RANDOM.randint(18, 72)
    vip_level = _weighted_vip()
    plan_id, monthly_fee = _pick_plan(vip_level)
    fee_drift = round(_RANDOM.uniform(-0.05, 0.35), 2)
    network_type = "5G" if age < 55 and _RANDOM.random() < 0.78 else _RANDOM.choice(NETWORK_TYPES)
    join_date = date.today() - timedelta(days=_RANDOM.randint(30, 3650))
    return {
        "user_id": _next_user_id(),
        "name": _RANDOM.choice(SURNAMES) + _RANDOM.choice(GIVEN_NAMES),
        "age": age,
        "age_group": age_to_group(age),
        "region_l1": province,
        "region_l2": city,
        "region": f"{province}·{city}",
        "plan_id": plan_id,
        "vip_level": vip_level,
        "join_date": join_date,
        "monthly_fee": monthly_fee,
        "fee_drift_rate": fee_drift,
        "_network_type": network_type,
        "_device": _RANDOM.choice(DEVICES),
        "_province": province,
        "_city": city,
    }


def strip_seed_meta(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}
