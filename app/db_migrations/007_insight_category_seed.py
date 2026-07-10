"""投诉一二级分类种子数据（幂等）。"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

# 一级 → 二级
_CATEGORY_TREE: dict[str, list[str]] = {
    "网络": ["速度慢", "掉线", "延迟", "信号差", "覆盖不足"],
    "客服": ["态度差", "响应慢", "推诿扯皮", "专业不足", "转接繁琐"],
    "扣费": ["莫名扣费", "账单异议", "退款拖延", "增值业务", "重复扣费"],
    "套餐": ["资费不透明", "套餐变更", "合约纠纷", "流量争议", "提速降费"],
    "APP": ["闪退卡顿", "功能异常", "登录困难", "界面难用", "更新问题"],
    "终端": ["质量问题", "售后服务", "维修拖延", "以旧换新", "配件问题"],
    "营业厅": ["排队过长", "办理效率", "业务差错", "设施环境", "预约困难"],
    "其它": ["其他问题"],
}


def upgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM insight_complaint_categories WHERE level = 1 LIMIT 1")
        ).first()
        if exists:
            return

        for sort_order, (primary, children) in enumerate(_CATEGORY_TREE.items(), start=1):
            parent_id = conn.execute(
                text(
                    """
                    INSERT INTO insight_complaint_categories (parent_id, name, level, sort_order)
                    VALUES (NULL, :name, 1, :sort_order)
                    RETURNING id
                    """
                ),
                {"name": primary, "sort_order": sort_order},
            ).scalar_one()
            for sub_order, sub_name in enumerate(children, start=1):
                conn.execute(
                    text(
                        """
                        INSERT INTO insight_complaint_categories
                            (parent_id, name, level, sort_order)
                        VALUES (:parent_id, :name, 2, :sort_order)
                        """
                    ),
                    {"parent_id": parent_id, "name": sub_name, "sort_order": sub_order},
                )
