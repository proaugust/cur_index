import json

LOGISTICS_DELAY = "物流延迟"

# 中性种子句：不含口语词，仅用于定义类别语义
CATEGORY_SEEDS: dict[str, dict] = {
    LOGISTICS_DELAY: {
        "description": "包裹配送、快递运输、物流环节出现的延误问题",
        "seed_phrases": [
            "包裹配送时间超过预期",
            "快递物流运输出现延误",
            "订单发货后长时间未送达",
            "物流配送进度停滞",
            "货物运输途中延迟",
        ],
    },
    "客服态度": {
        "description": "客服人员沟通态度、服务质量相关问题",
        "seed_phrases": [
            "客服人员态度恶劣",
            "客服回复敷衍不解决问题",
            "联系客服体验很差",
            "客服推诿扯皮",
            "售后客服不负责任",
        ],
    },
    "商品质量": {
        "description": "商品本身质量、破损、与描述不符等问题",
        "seed_phrases": [
            "收到的商品存在质量问题",
            "产品实物与描述不符",
            "商品包装破损影响使用",
            "货物有瑕疵需要退换",
            "商品功能异常无法正常使用",
        ],
    },
}


def dumps_seed_phrases(phrases: list[str]) -> str:
    return json.dumps(phrases, ensure_ascii=False)
