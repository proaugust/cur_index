"""用户画像造数：insight_user_profile 静态字段。"""

import random
from datetime import date, timedelta

from app.services.modules.insight.constants import (
    CHANNELS,
    DEVICES,
    GENDERS,
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


def _fake_msisdn() -> str:
    prefix = _RANDOM.choice(("130", "131", "135", "138", "150", "151", "186", "188"))
    return f"{prefix}{_RANDOM.randint(0, 99999999):08d}"


def generate_profile_row() -> dict:
    province, city = _pick_region()
    age = _RANDOM.randint(18, 72)
    vip_level = _weighted_vip()
    plan_id, monthly_fee = _pick_plan(vip_level)
    fee_drift = round(_RANDOM.uniform(-0.05, 0.35), 2)
    network_type = "5G" if age < 55 and _RANDOM.random() < 0.78 else _RANDOM.choice(NETWORK_TYPES)
    join_date = date.today() - timedelta(days=_RANDOM.randint(30, 3650))
    contract_end = join_date + timedelta(days=_RANDOM.choice((365, 730, 1095)))
    # 问卷维度满意分（1～5）；样本真值 sample_satisfaction 仅由样本合并写入
    satisfaction_net = _RANDOM.choices([1, 2, 3, 4, 5], weights=[5, 12, 35, 30, 18])[0]
    satisfaction_srv = _RANDOM.choices([1, 2, 3, 4, 5], weights=[5, 12, 35, 30, 18])[0]
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
        "gender": _RANDOM.choice(GENDERS),
        "msisdn": _fake_msisdn(),
        "channel": _RANDOM.choice(CHANNELS),
        "device_brand": _RANDOM.choice(DEVICES),
        "network_type": network_type,
        "contract_end": contract_end,
        "satisfaction_net": satisfaction_net,
        "satisfaction_srv": satisfaction_srv,
        "_province": province,
        "_city": city,
    }


def strip_seed_meta(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}
