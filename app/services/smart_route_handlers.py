"""智能路由 — 各业务接口占位实现（展示阶段不调用，后续在此补全）。"""


def query_weather(question: str) -> str:
    """天气查询接口：根据用户问题返回天气信息。"""
    # TODO: 对接天气 API 或内部天气服务
    raise NotImplementedError


def query_employee(question: str) -> str:
    """员工知识库检索接口：根据姓名或条件查询员工档案。"""
    # TODO: 对接知识库 / HR 系统检索
    raise NotImplementedError


def send_email(question: str) -> str:
    """邮件发送接口：解析收件人与正文并发送邮件。"""
    # TODO: 对接邮件服务（SMTP / 企业邮 API）
    raise NotImplementedError


def query_general(question: str) -> str:
    """通用问答接口：无法匹配具体业务时的兜底处理。"""
    # TODO: 转交通用对话或人工客服
    raise NotImplementedError
