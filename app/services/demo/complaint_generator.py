import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.demo.complaint_categories import CATEGORY_SEEDS

_COUNT = 500
_RANDOM = random.Random(42)

_ADDRESSES = ["千代田区","中央区","港区","新宿区","文京区","台东区","墨田区","江东区","品川区",
"目黑区","大田区","世田谷区","涩谷区","板桥区"]

_CATEGORY_TEMPLATES: dict[str, list[str]] = {
    "网络与信号质量": [
        "家里WiFi慢得要命，看视频一直转圈",
        "宽带天天断网，路由器闪红灯",
        "5G信号满格网页打不开，离谱",
        "卧室打个电话都断断续续",
        "网速测出来才几兆，跟套餐差太远",
        "一刮风下雨网络就挂，受不了",
        "远程开会老是掉线，耽误工作了",
        "卧室几乎收不到信号",
        "宽带频繁断连，路由器重启也没用",
        "看视频经常缓冲，卡到没法看",
        "WiFi在客厅能用，进卧室就没信号",
        "办理的千兆宽带实际只有几十兆",
    ],
    "售后与维保服务": [
        "报修三天了师傅还不来",
        "电视坏了报修，催了五遍没人理",
        "刚买两个月就故障，说要自费维修真气人",
        "售后电话打不通，一直在排队",
        "说二十四小时内上门，拖了一周",
        "维修来了两遍还是没修好",
        "保修期内不给换，只会推诿",
        "上门维修态度差，修完问题还在",
        "报修五天无人上门处理",
        "多次催促售后无果，太失望了",
        "刚买不久出现故障，售后不管",
        "对售后处理表示强烈不满",
    ],
    "客服与渠道体验": [
        "打客服等了四十分钟，接起来还甩脸色",
        "客服一直打断我说话，根本不想解决问题",
        "问个问题客服就会念脚本，敷衍死了",
        "营业厅就开两个窗口，排了两小时",
        "线上客服说完就挂断，太嚣张了",
        "去营业厅办业务被当皮球踢",
        "投诉后客服回电态度更差",
        "机器人客服绕圈子，转人工永远繁忙",
        "客服人员态度恶劣，体验极差",
        "客服多次打断我发言，气死了",
        "电话客服无故挂断，没人管",
        "营业厅排队时间过长，只开少量窗口",
    ],
    "资费与账单争议": [
        "莫名其妙多扣了五十块，也没通知我",
        "自动续费没提醒，银行卡被扣了",
        "账单比上月多了好多，查不明白",
        "充值一百块没到账，催了两天",
        "套餐外的流量费高得离谱",
        "说是免费试用结果直接扣费",
        "账单里多了个增值业务，我都没开过",
        "扣费短信来晚三天，钱早就没了",
        "自动续费未提前通知就扣款",
        "银行卡被异常扣款，要求退款",
        "账单费用比上月明显增加",
        "充值后长时间未到账",
    ],
    "硬件产品质量": [
        "手机充电烫手，外壳都裂了",
        "路由器用一个月就烧坏了",
        "机顶盒开机有异响，指示灯乱闪",
        "买的手机和宣传完全不一样",
        "光猫天天重启，质量太差",
        "设备有安全隐患，敢不敢召回",
        "新手机电池一天三充，续航骗人的",
        "摄像头晚上全是雪花，这啥质量",
        "充电时发烫严重，外壳开裂了",
        "设备运行有异响，指示灯异常",
        "实际产品功能跟宣传不符",
        "硬件故障频发，根本没法用",
    ],
    "账户安全与隐私": [
        "号被盗刷了三百多，平台不赔",
        "账号异地登录也没提醒",
        "个人信息泄露后骚扰电话暴增",
        "收到一堆验证码，怀疑被卖了信息",
        "家人号码被冒用办了业务",
        "账户资金被盗，客服只会推诿",
        "注销了账号还在收营销短信",
        "实名信息被泄露，接到诈骗电话",
        "用户账号被盗，损失不少钱",
        "收到大量骚扰短信，怀疑平台泄露信息",
        "要求平台先行赔付被盗资金",
        "账号安全问题没人负责",
    ],
    "营销与骚扰": [
        "说了不要还天天打电话推销套餐",
        "退订短信发了十几次还在打",
        "半夜营销电话吵醒孩子",
        "冒充客服推销，烦不胜烦",
        "已加入黑名单还能打进来",
        "一天三个推销电话，能不能别打了",
        "擅自开通营销业务，没人问过我就办",
        "外呼公司换着号码骚扰",
        "未经同意频繁营销来电",
        "退订后仍收到推销电话",
        "深夜营销电话打扰休息",
        "营销短信轰炸停不下来",
    ],
    "套餐变更与销户": [
        "没经过同意就给我改了套餐",
        "想降套餐各种理由不让办",
        "销户跑三趟营业厅还是退不了",
        "携号转网被故意刁难",
        "合约没到期不让改套餐，霸王条款",
        "线上说能办，到了营业厅又不行",
        "套餐升级容易降级难，什么套路",
        "销户还要交违约金，事先没告知",
        "未经同意变更套餐，太霸王了",
        "申请降档套餐一直被拒",
        "销户多次办理仍未成功",
        "携号转网办理受到阻碍",
    ],
}


@dataclass(frozen=True)
class ComplaintSeedItem:
    complaint_text: str
    address: str
    complaint_time: datetime


def _random_complaint_time() -> datetime:
    days_ago = _RANDOM.randint(0, 30)
    hour = _RANDOM.randint(8, 22)
    minute = _RANDOM.randint(0, 59)
    base = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base - timedelta(days=days_ago)


def _generate_for_category(category_name: str, count: int, seen: set[str]) -> list[ComplaintSeedItem]:
    templates = _CATEGORY_TEMPLATES[category_name]
    results: list[ComplaintSeedItem] = []
    attempts = 0
    max_attempts = count * 30

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        text = _RANDOM.choice(templates)
        if text in seen:
            continue
        seen.add(text)
        results.append(
            ComplaintSeedItem(complaint_text=text, address=_RANDOM.choice(_ADDRESSES), complaint_time=_random_complaint_time())
        )
    return results


def generate_complaints(count: int = _COUNT) -> list[ComplaintSeedItem]:
    category_names = list(CATEGORY_SEEDS.keys())
    per_category = count // len(category_names)
    remainder = count % len(category_names)

    seen: set[str] = set()
    results: list[ComplaintSeedItem] = []

    for index, category_name in enumerate(category_names):
        target = per_category + (1 if index < remainder else 0)
        results.extend(_generate_for_category(category_name, target, seen))

    _RANDOM.shuffle(results)
    return results
