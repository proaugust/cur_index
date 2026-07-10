"""特征名与业务中文标签映射。"""

from app.services.modules.insight.seed.survey_generator import SURVEY_QUESTION_BANK

VIP_ORDINAL = {"普通": 0, "银卡": 1, "金卡": 2, "钻石": 3}

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

PROFILE_NUMERIC = (
    "age",
    "monthly_fee",
    "fee_drift_rate",
    "satisfaction_net",
    "satisfaction_srv",
    "vip_ord",
    "join_tenure_years",
)

SAMPLE_NUMERIC = ("sample_cnt", "complaint_cnt", "avg_satisfaction")

FEATURE_NAMES: list[str] = [
    *PROFILE_NUMERIC,
    *SAMPLE_NUMERIC,
    *(f"ctype_{name}" for name in COMPLAINT_TYPE_KEYS),
    *(f"survey_{key}" for key in SURVEY_KEYS),
]

FEATURE_LABELS: dict[str, str] = {
    "age": "年龄",
    "monthly_fee": "月费",
    "fee_drift_rate": "账单变动率",
    "satisfaction_net": "网络满意度",
    "satisfaction_srv": "服务满意度",
    "vip_ord": "会员等级",
    "join_tenure_years": "入网年限",
    "sample_cnt": "问卷样本数",
    "complaint_cnt": "投诉次数",
    "avg_satisfaction": "满意度均分",
    **{f"ctype_{name}": f"投诉·{name}" for name in COMPLAINT_TYPE_KEYS},
    **{f"survey_{key}": label for key, label, _ in SURVEY_QUESTION_BANK},
}


def label_shap(feature_name: str) -> str:
    return FEATURE_LABELS.get(feature_name, feature_name)
