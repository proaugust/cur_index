"""问卷样本造数：10 类 50 题写入 JSONB。"""

import random
from decimal import Decimal

_RANDOM = random.Random(88)

SURVEY_QUESTION_BANK: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("network_quality", "网络质量", ("通话是否清晰稳定？", "移动网络是否经常掉线？", "高峰时段网速是否满意？", "室内信号覆盖是否满意？", "视频播放是否流畅？")),
    ("billing_fee", "资费账单", ("账单金额是否清晰？", "套餐资费是否合理？", "扣费通知是否及时？", "优惠活动是否容易理解？", "费用变动是否可接受？")),
    ("customer_service", "客服服务", ("客服响应是否及时？", "问题解释是否清楚？", "处理态度是否满意？", "一次解决率是否满意？", "回访服务是否满意？")),
    ("package_value", "套餐价值", ("套餐流量是否够用？", "语音分钟数是否合适？", "权益内容是否实用？", "套餐升级推荐是否合理？", "套餐性价比是否满意？")),
    ("app_experience", "App体验", ("App 登录是否顺畅？", "业务办理是否方便？", "页面信息是否清晰？", "查询账单是否容易？", "线上客服是否好用？")),
    ("shop_experience", "门店体验", ("门店排队时间是否可接受？", "工作人员解释是否专业？", "业务办理是否高效？", "门店环境是否满意？", "材料要求是否清楚？")),
    ("device_service", "终端服务", ("终端兼容性是否满意？", "换机迁移是否方便？", "SIM/eSIM 办理是否顺畅？", "终端维修指引是否清楚？", "设备优惠是否有吸引力？")),
    ("roaming_service", "漫游服务", ("国内漫游体验是否稳定？", "国际漫游开通是否方便？", "漫游费用是否清楚？", "异地服务是否一致？", "旅行场景网络是否满意？")),
    ("privacy_security", "隐私安全", ("验证码保护是否可靠？", "账号登录提醒是否及时？", "隐私授权是否清楚？", "骚扰拦截是否有效？", "风险提示是否有帮助？")),
    ("loyalty_retention", "忠诚留存", ("会员权益是否有价值？", "老用户优惠是否满意？", "续约体验是否顺畅？", "推荐亲友意愿如何？", "整体继续使用意愿如何？")),
)


def build_survey_row() -> dict:
    answers = []
    category_scores: dict[str, float] = {}
    for category_key, category_name, questions in SURVEY_QUESTION_BANK:
        scores = []
        for index, question in enumerate(questions, start=1):
            score = _RANDOM.randint(1, 5)
            scores.append(score)
            answers.append(
                {
                    "question_id": f"{category_key.upper()}_{index:02d}",
                    "category_key": category_key,
                    "category_name": category_name,
                    "question": question,
                    "score": score,
                }
            )
        category_scores[category_key] = round(sum(scores) / len(scores), 2)

    total_score = round(sum(item["score"] for item in answers) / len(answers), 2)
    return {
        "survey_answers": answers,
        "survey_category_scores": category_scores,
        "satisfaction_score": Decimal(str(total_score)),
    }
