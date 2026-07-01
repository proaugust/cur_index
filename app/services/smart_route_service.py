import logging

from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.core.config import settings
from app.services.llm import chat_completion
from app.services.smart_route_handlers import query_employee, query_weather

logger = logging.getLogger(__name__)

_ROUTE_SYSTEM = (
    "你是业务意图路由器。根据用户的一句话，判断应走哪条后端接口。\n"
    "只输出以下四个标签之一，不要输出其他任何内容：\n"
    "- weather（天气、气温、下雨、晴天等）\n"
    "- employee（查员工、人员信息、工号、部门、U0001 等）\n"
    "- email（发邮件、邮件通知、发送邮件等）\n"
    "- unknown（与以上三类均无关）"
)

_INTENT_MESSAGES: dict[str, str] = {
    "weather": "调用了天气查询接口",
    "employee": "调用了员工知识库检索接口",
    "email": "调用了邮件发送接口",
    "unknown": "未匹配到具体业务，调用了通用问答接口",
}

_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("email", ["邮件", "发邮件", "发送邮件", "写邮件", "mail"]),
    ("weather", ["天气", "气温", "温度", "下雨", "晴天", "刮风", "预报"]),
    ("employee", ["员工", "人员", "工号", "部门", "档案", "人事", "打卡", "U0001"]),
]


def _normalize_intent(raw: str) -> str:
    text = raw.strip().lower()
    for key in ("weather", "employee", "email", "unknown"):
        if key in text:
            return key
    for key, keywords in _KEYWORD_RULES:
        if any(kw in raw for kw in keywords):
            return key
    return "unknown"


def _classify_by_keywords(question: str) -> str:
    for intent, keywords in _KEYWORD_RULES:
        if any(kw in question for kw in keywords):
            return intent
    return "unknown"


def _classify_by_llm(question: str) -> str:
    if not settings.openai_api_key:
        return _classify_by_keywords(question)
    try:
        answer = chat_completion(_ROUTE_SYSTEM, question, temperature=0.1, caller="smart_route.dispatch")
        return _normalize_intent(answer)
    except HTTPException:
        logger.warning("智能路由 LLM 分类失败，回退关键词规则", exc_info=True)
        return _classify_by_keywords(question)


def route_question(question: str, db: Session) -> tuple[str, str, list]:
    """根据用户问题判断意图，返回 (intent, 展示文案, 员工列表)。"""
    text = question.strip()
    if not text:
        raise HTTPException(status_code=400, detail="问题不能为空")

    intent = _classify_by_llm(text)
    employees: list = []
    if intent == "weather":
        message = query_weather(text)
    elif intent == "employee":
        message, employees = query_employee(text, db)
    else:
        message = _INTENT_MESSAGES[intent]
    return intent, message, employees
