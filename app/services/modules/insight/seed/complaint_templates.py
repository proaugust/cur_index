"""投诉正文模板库：按一级×二级分类，80~150 字自然描述。"""

import random
from typing import Any

_RANDOM = random.Random(2026)

# (complaint_type, sub_type) → 模板列表；{key} 由上下文填充
TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("网络质量", "速度慢"): [
        "我是{package_type}用户，月费{monthly_fee}元，住在{province}{city}，使用{device}通过{network_type}上网。"
        "最近一周网速明显下降，测速只有{speed_mbps}Mbps，看视频和远程办公都很卡，希望排查是否基站拥塞或线路问题。",
        "办理的是{package_type}，承诺带宽与实际差距较大，{city}家中晚高峰下载经常不到{speed_mbps}兆，"
        "已重启光猫和路由器无效，请安排技术人员上门检测。",
    ],
    ("网络质量", "掉线"): [
        "作为{vip_level}客户，{province}{city}家中宽带频繁掉线，平均每天断网{drop_times}次，"
        "每次需等待{wait_minutes}分钟才能恢复，严重影响孩子网课，请尽快处理线路稳定性问题。",
    ],
    ("网络质量", "延迟"): [
        "我用{device}连接{network_type}打游戏延迟长期在{latency_ms}ms以上，{city}片区朋友同款套餐正常，"
        "怀疑本地节点有问题，请协助优化路由或更换接入方式。",
    ],
    ("网络质量", "信号差"): [
        "{province}{city}{building}室内{network_type}信号偏弱，客厅仅一格，卧室经常无服务，"
        "我是{package_type}老用户，请评估是否需要加装信号放大或调整附近基站。",
    ],
    ("网络质量", "覆盖不足"): [
        "出差至{province}{city}郊区，{network_type}几乎无法使用，地图显示应有覆盖但实际无法通话上网，"
        "请核实该区域基站建设规划，并告知预计改善时间。",
    ],
    ("客服", "态度差"): [
        "本月{day}日拨打客服反映账单问题，工号{agent_no}接待时语气生硬，多次打断我说明情况，"
        "作为{package_type}用户感到不被尊重，希望加强服务培训并回电道歉。",
    ],
    ("客服", "响应慢"): [
        "通过APP在线客服反映{sub_type}问题，排队超过{wait_minutes}分钟才接入，之后又说需要{follow_days}个工作日回复，"
        "问题至今未解决，请提升响应效率。",
    ],
    ("客服", "推诿扯皮"): [
        "就{sub_type}问题已被转接{transfer_times}次，各部门都说不在职责范围，"
        "我是{vip_level}用户，月消费{monthly_fee}元，请指定专人跟进到底。",
    ],
    ("客服", "专业不足"): [
        "咨询{package_type}流量结转规则，客服答复前后矛盾，与官网说明不一致，"
        "担心被误导办理业务，请书面澄清规则并回电确认。",
    ],
    ("客服", "转接繁琐"): [
        "反映{device}无法正常使用，先被转网络组再转终端组，合计等待{wait_minutes}分钟仍未解决，"
        "请优化一键直达流程，减少重复描述。",
    ],
    ("扣费", "莫名扣费"): [
        "我是{monthly_fee}元档{package_type}用户，本月账单突然出现{extra_fee}元增值费用，"
        "本人未开通相关业务，请核查扣费来源并全额退还。",
    ],
    ("扣费", "账单异议"): [
        "我是{package_type}用户，家住{province}{city}，本月账单比上个月多了{extra_fee}元，"
        "客服解释不清楚明细，希望核查扣费原因，如属误扣请退款并短信告知处理结果。",
    ],
    ("扣费", "退款拖延"): [
        "已确认{extra_fee}元属于误扣，{refund_days}天前承诺三个工作日退回，至今未到账，"
        "请加快退款进度并补偿期间影响。",
    ],
    ("扣费", "增值业务"): [
        "账单中出现{value_added}业务费用，我未在短信或APP中确认订购，"
        "怀疑被默认开通，请立即取消并退还最近三个月相关费用。",
    ],
    ("扣费", "重复扣费"): [
        "同一账单周期内{package_type}基础费被扣了{duplicate_times}次，合计多扣{extra_fee}元，"
        "请核对计费系统并退回重复部分。",
    ],
    ("套餐", "资费不透明"): [
        "办理{package_type}时口头承诺月费{monthly_fee}元，实际账单含多项附加费用，"
        "请提供完整资费说明并恢复承诺价格。",
    ],
    ("套餐", "套餐变更"): [
        "申请将{package_type}变更为更低档位，营业厅称需满{contract_months}个月，"
        "但当初未明确告知合约限制，请协助合理解约或减免违约金。",
    ],
    ("套餐", "合约纠纷"): [
        "合约到期后仍按原价{monthly_fee}元扣费，未收到续约确认，"
        "请按最新公示资费调整并退还多收部分。",
    ],
    ("套餐", "流量争议"): [
        "本月流量使用{used_gb}GB即被限速，与{package_type}宣传不符，"
        "请核实计费流量明细并恢复网速。",
    ],
    ("套餐", "提速降费"): [
        "同小区邻居已享受降费政策，我仍为{monthly_fee}元旧套餐，"
        "请核实是否可无损迁移至同等权益的新套餐。",
    ],
    ("APP", "闪退卡顿"): [
        "使用官方APP查询账单时频繁闪退，{device}系统版本较新，重装后仍卡顿，"
        "请修复兼容问题，影响我及时核对{extra_fee}元异常扣费。",
    ],
    ("APP", "功能异常"): [
        "APP内无法办理{package_type}续费，点击后白屏，已持续{follow_days}天，"
        "请尽快修复以免影响正常使用。",
    ],
    ("APP", "登录困难"): [
        "验证码登录多次提示系统繁忙，{wait_minutes}分钟内尝试{try_times}次均失败，"
        "请检查认证服务并恢复登录。",
    ],
    ("APP", "界面难用"): [
        "新版APP账单入口隐藏过深，老年人用户难以找到缴费入口，"
        "建议优化信息架构，同时恢复旧版常用功能。",
    ],
    ("APP", "更新问题"): [
        "强制更新后无法查看历史账单，提示权限错误，请回滚或紧急修复该模块。",
    ],
    ("终端", "质量问题"): [
        "购买的{device}使用{use_months}个月后出现发热和自动关机，"
        "仍在保修期内，请安排检测或更换。",
    ],
    ("终端", "售后服务"): [
        "报修{device}后门店称需自费更换配件，与三包政策不符，"
        "请协调正规售后并书面说明收费依据。",
    ],
    ("终端", "维修拖延"): [
        "终端送修已{repair_days}天，多次催促仅回复缺件，"
        "请给出明确取机时间或提供备用机。",
    ],
    ("终端", "以旧换新"): [
        "参与以旧换新估价与到店检测价差{extra_fee}元，流程不透明，"
        "请统一评估标准并补足差额说明。",
    ],
    ("终端", "配件问题"): [
        "原装充电器异常发热，担心安全隐患，请更换合格配件并检测主机接口。",
    ],
    ("营业厅", "排队过长"): [
        "{province}{city}{store_name}周末仅开放{window_count}个窗口，排队超过{wait_minutes}分钟，"
        "请增加高峰时段人手或引导线上办理。",
    ],
    ("营业厅", "办理效率"): [
        "办理套餐变更耗时近{wait_minutes}分钟，反复填表和复印证件，"
        "请优化流程，避免老客户重复提交材料。",
    ],
    ("营业厅", "业务差错"): [
        "营业员误将{package_type}办理为更高档位，导致月费多{extra_fee}元，"
        "请更正套餐并退还差额。",
    ],
    ("营业厅", "设施环境"): [
        "营业厅等候区座位不足，且无叫号进度显示，老人站立不便，"
        "请改善现场服务设施。",
    ],
    ("营业厅", "预约困难"): [
        "连续{try_times}天网上预约均显示已满，现场却要等{wait_minutes}分钟，"
        "请增加可预约名额并同步库存。",
    ],
    ("其它", "其他问题"): [
        "我是{package_type}用户，近期在{province}{city}遇到综合服务质量问题，"
        "已多次反馈未获满意答复，请安排专员回访并给出书面处理方案。",
    ],
}

_DEFAULT_TEMPLATE = (
    "我是{package_type}用户，月费约{monthly_fee}元，位于{province}{city}，"
    "近期遇到{complaint_type}-{sub_type}相关问题，请尽快核实并回复处理进度。"
)


def _base_context(customer: dict[str, Any], pair: dict[str, str]) -> dict[str, Any]:
    monthly = float(customer.get("monthly_fee") or 199)
    return {
        **customer,
        **pair,
        "monthly_fee": int(monthly) if monthly == int(monthly) else monthly,
        "extra_fee": _RANDOM.choice([18, 28, 38, 58, 68, 88]),
        "wait_minutes": _RANDOM.choice([15, 25, 35, 45, 60, 90]),
        "follow_days": _RANDOM.choice([3, 5, 7, 10]),
        "transfer_times": _RANDOM.choice([2, 3, 4]),
        "drop_times": _RANDOM.choice([3, 5, 8]),
        "speed_mbps": _RANDOM.choice([8, 12, 20, 35]),
        "latency_ms": _RANDOM.choice([120, 180, 260, 320]),
        "building": _RANDOM.choice(["小区", "写字楼", "商住楼"]),
        "day": _RANDOM.choice([3, 8, 12, 18, 22]),
        "agent_no": f"{_RANDOM.randint(1000, 9999)}",
        "refund_days": _RANDOM.choice([5, 7, 10, 14]),
        "value_added": _RANDOM.choice(["视频会员", "彩铃包", "云盘权益", "安全卫士"]),
        "duplicate_times": 2,
        "contract_months": _RANDOM.choice([12, 24, 36]),
        "used_gb": _RANDOM.choice([40, 60, 80, 120]),
        "use_months": _RANDOM.choice([3, 6, 9, 12]),
        "repair_days": _RANDOM.choice([7, 10, 15, 20]),
        "store_name": _RANDOM.choice(["中心营业厅", "高新区营业厅", "人民路营业厅"]),
        "window_count": _RANDOM.choice([2, 3]),
        "try_times": _RANDOM.choice([3, 5, 7]),
    }


def render_complaint_text(pair: dict[str, str], customer: dict[str, Any]) -> str:
    key = (pair["complaint_type"], pair["sub_type"])
    templates = TEMPLATES.get(key) or [_DEFAULT_TEMPLATE]
    template = _RANDOM.choice(templates)
    ctx = _base_context(customer, pair)
    text = template.format(**ctx)
    # 控制在 80~150 字左右；过长则截断到完整句
    if len(text) > 150:
        text = text[:150]
        for sep in ("。", "，", "；"):
            idx = text.rfind(sep)
            if idx >= 80:
                text = text[: idx + 1]
                break
    return text
