"""特征名与业务中文标签映射。"""

from app.services.modules.insight.constants import (
    CHANNELS,
    DEVICES,
    GENDERS,
    NETWORK_TYPES,
    PLAN_FEES,
    REGION_CITIES,
    VIP_LEVELS,
)
from app.services.modules.insight.seed.survey_generator import SURVEY_QUESTION_BANK

VIP_ORDINAL = {name: idx for idx, name in enumerate(VIP_LEVELS)}
GENDER_ORDINAL = {name: idx for idx, name in enumerate(GENDERS)}
CHANNEL_ORDINAL = {name: idx for idx, name in enumerate(CHANNELS)}
NETWORK_ORDINAL = {name: idx for idx, name in enumerate(NETWORK_TYPES)}
DEVICE_ORDINAL = {name: idx for idx, name in enumerate(DEVICES)}
PLAN_ORDINAL = {name: idx for idx, name in enumerate(PLAN_FEES.keys())}
AGE_GROUP_ORDINAL = {
    "18-25": 0,
    "26-35": 1,
    "36-45": 2,
    "46-55": 3,
    "56+": 4,
}
REGION_L1_ORDINAL = {name: idx for idx, name in enumerate(REGION_CITIES.keys())}
REGION_L2_ORDINAL = {
    city: idx
    for idx, city in enumerate(city for cities in REGION_CITIES.values() for city in cities)
}
REGION_ORDINAL = {
    f"{province}·{city}": idx
    for idx, (province, city) in enumerate(
        (province, city) for province, cities in REGION_CITIES.items() for city in cities
    )
}

SURVEY_KEYS = tuple(key for key, _, _ in SURVEY_QUESTION_BANK)

COMPLAINT_TYPE_KEYS = (
    "网络质量",
    "客服",
    "扣费",
    "套餐",
    "APP",
    "终端",
    "营业厅",
    "其它",
)

# 对齐「注入客户」列表：性别 → 资费漂移（含手机号、区域全文）
PROFILE_NUMERIC = (
    "gender_ord",
    "msisdn_num",
    "age",
    "age_group_ord",
    "region_l1_ord",
    "region_l2_ord",
    "region_ord",
    "plan_ord",
    "vip_ord",
    "channel_ord",
    "device_ord",
    "network_ord",
    "join_tenure_years",
    "contract_remain_years",
    "monthly_fee",
    "fee_drift_rate",
)

SAMPLE_NUMERIC = ("sample_cnt", "complaint_cnt", "avg_satisfaction")

# 对齐合成标签 DGP：近窗投诉 + 满意度缺口 + 交互项
DERIVED_NUMERIC = (
    "complaint_cnt_30d",
    "sat_gap",
    "ix_complaint_sat_gap",
    "ix_fee_loyalty_gap",
)

FEATURE_NAMES: list[str] = [
    *PROFILE_NUMERIC,
    *SAMPLE_NUMERIC,
    *(f"ctype_{name}" for name in COMPLAINT_TYPE_KEYS),
    *(f"survey_{key}" for key in SURVEY_KEYS),
    *DERIVED_NUMERIC,
]

FEATURE_LABELS: dict[str, str] = {
    "gender_ord": "性别",
    "msisdn_num": "手机号",
    "age": "年龄",
    "age_group_ord": "年龄段",
    "region_l1_ord": "省/都道府",
    "region_l2_ord": "市/区",
    "region_ord": "区域",
    "plan_ord": "套餐",
    "vip_ord": "会员等级",
    "channel_ord": "入网渠道",
    "device_ord": "终端",
    "network_ord": "网络",
    "join_tenure_years": "入网年限",
    "contract_remain_years": "合约剩余年",
    "monthly_fee": "月费",
    "fee_drift_rate": "资费漂移",
    "sample_cnt": "问卷样本数",
    "complaint_cnt": "投诉次数",
    "avg_satisfaction": "满意度均分",
    "complaint_cnt_30d": "近30天投诉",
    "sat_gap": "满意度缺口",
    "ix_complaint_sat_gap": "投诉×满意度缺口",
    "ix_fee_loyalty_gap": "账单变动×忠诚缺口",
    **{f"ctype_{name}": f"投诉·{name}" for name in COMPLAINT_TYPE_KEYS},
    **{f"survey_{key}": label for key, label, _ in SURVEY_QUESTION_BANK},
}


def label_shap(feature_name: str) -> str:
    return FEATURE_LABELS.get(feature_name, feature_name)


def _ord(mapping: dict[str, int], value: str | None, default: float = -1.0) -> float:
    if value is None:
        return default
    return float(mapping.get(value, default))


def msisdn_num(msisdn: str | None) -> float:
    """手机号编码为数值（取数字后缀）；空则 -1。"""
    if not msisdn:
        return -1.0
    digits = "".join(ch for ch in msisdn if ch.isdigit())
    if not digits:
        return -1.0
    return float(int(digits[-10:]))
