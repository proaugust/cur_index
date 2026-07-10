"""客户洞察模块常量与造数预设。"""

from typing import Literal

InsightPreset = Literal["mini", "dev", "demo", "full"]

SEED_PRESETS: dict[InsightPreset, dict[str, int]] = {
    "mini": {"users": 100, "complaints": 100, "touchpoints": 100},
    "dev": {"users": 10_000, "complaints": 500, "touchpoints": 500},
    "demo": {"users": 100_000, "complaints": 3_000, "touchpoints": 3_000},
    "full": {"users": 500_000, "complaints": 5_000, "touchpoints": 5_000},
}

USER_BATCH_SIZE = 5_000
SAMPLE_BATCH_SIZE = 1_000
# HF/托管 PG 常有 statement_timeout；快照含 JSONB，单批不宜过大
SNAPSHOT_WRITE_BATCH_SIZE = 500
COMPLAINT_VECTOR_DIM = 768

SURNAMES = ("张", "李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "胡", "朱", "高", "林")
GIVEN_NAMES = ("伟", "芳", "娜", "敏", "静", "强", "磊", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀英")

VIP_LEVELS = ("普通", "银卡", "金卡", "钻石")
NETWORK_TYPES = ("4G", "5G")
DEVICES = (
    "iPhone 15",
    "iPhone 14",
    "Huawei Mate 60",
    "Huawei P60",
    "Xiaomi 14",
    "OPPO Find X7",
    "vivo X100",
    "Honor Magic6",
    "Samsung S24",
    "Redmi Note 13",
)

REGION_CITIES: dict[str, list[str]] = {
    "东京都": [
        "千代田区",
        "中央区",
        "港区",
        "新宿区",
        "文京区",
        "台东区",
        "墨田区",
        "江东区",
        "品川区",
        "目黑区",
        "大田区",
        "世田谷区",
        "涩谷区",
        "中野区",
        "杉并区",
        "丰岛区",
        "北区",
        "荒川区",
        "板桥区",
        "练马区",
        "足立区",
        "葛饰区",
        "江户川区",
    ],
    "神奈川县": [
        "横滨市鹤见区",
        "横滨市神奈川区",
        "横滨市西区",
        "横滨市中区",
        "横滨市港北区",
        "横滨市青叶区",
        "川崎市川崎区",
        "川崎市中原区",
        "川崎市高津区",
        "相模原市中央区",
    ],
    "千叶县": [
        "千叶市中央区",
        "千叶市花见川区",
        "千叶市稻毛区",
        "千叶市美浜区",
        "船桥市",
        "市川市",
        "松户市",
        "柏市",
        "浦安市",
        "习志野市",
    ],
    "埼玉县": [
        "埼玉市西区",
        "埼玉市北区",
        "埼玉市大宫区",
        "埼玉市浦和区",
        "埼玉市南区",
        "川口市",
        "川越市",
        "越谷市",
        "所泽市",
        "草加市",
    ],
    "茨城县": ["水户市", "筑波市", "日立市", "土浦市", "古河市"],
    "栃木县": ["宇都宫市", "小山市", "栃木市", "足利市", "那须盐原市"],
    "群马县": ["前桥市", "高崎市", "太田市", "伊势崎市", "桐生市"],
    "山梨县": ["甲府市", "富士吉田市", "都留市", "山梨市", "大月市"],
    "静冈县": ["静冈市葵区", "滨松市中区", "沼津市", "富士市", "热海市"],
}

PLAN_FEES: dict[str, float] = {
    "99元套餐": 99.0,
    "129元套餐": 129.0,
    "159元套餐": 159.0,
    "199元套餐": 199.0,
    "239元套餐": 239.0,
    "299元套餐": 299.0,
    "399元套餐": 399.0,
    "599元套餐": 599.0,
}

# 投诉一二级分类（原 insight_complaint_categories 种子）
COMPLAINT_CATEGORY_TREE: dict[str, list[str]] = {
    "网络质量": ["速度慢", "掉线", "延迟", "信号差", "覆盖不足"],
    "客服": ["态度差", "响应慢", "推诿扯皮", "专业不足", "转接繁琐"],
    "扣费": ["莫名扣费", "账单异议", "退款拖延", "增值业务", "重复扣费"],
    "套餐": ["资费不透明", "套餐变更", "合约纠纷", "流量争议", "提速降费"],
    "APP": ["闪退卡顿", "功能异常", "登录困难", "界面难用", "更新问题"],
    "终端": ["质量问题", "售后服务", "维修拖延", "以旧换新", "配件问题"],
    "营业厅": ["排队过长", "办理效率", "业务差错", "设施环境", "预约困难"],
    "其它": ["其他问题"],
}

TOUCHPOINT_STEPS = ("网络劣化", "APP查询", "在线客服", "拨打客服", "营业厅到访", "投诉升级")
RISK_LEVELS = ((0.70, "高风险"), (0.40, "中风险"), (0.0, "低风险"))

# M2 单客画像：热点缓存阈值
PROFILE_HOT_RISK_THRESHOLD = 0.85
PROFILE_CACHE_TTL_SECONDS = 86400
PROFILE_RECENT_COMPLAINT_LIMIT = 5
PROFILE_RECENT_TOUCHPOINT_LIMIT = 10
PROFILE_HOT_COMPLAINT_MIN = 3
PROFILE_HOT_VIP_LEVELS = ("金卡", "钻石")


def age_to_group(age: int) -> str:
    if age <= 25:
        return "18-25"
    if age <= 35:
        return "26-35"
    if age <= 45:
        return "36-45"
    if age <= 55:
        return "46-55"
    return "56+"


def risk_score_to_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return "低风险"
