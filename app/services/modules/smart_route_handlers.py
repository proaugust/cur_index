"""智能路由 — 各业务接口实现。"""

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app import schemas
from app.services.modules import attendance_service
from app.services.modules.agent_common import extract_weather_city, run_weather_tool

_EMPLOYEE_ID_PATTERN = re.compile(r"U\d{4}", re.IGNORECASE)


def extract_employee_names(question: str) -> list[str] | None:
    """从问题中提取员工 user_id（仅 U0001 格式）；未指定时返回 None 表示查全部已登记人员。"""
    u_ids = [uid.upper() for uid in _EMPLOYEE_ID_PATTERN.findall(question)]
    if u_ids:
        return list(dict.fromkeys(u_ids))
    return None


def _to_smart_route_employee(profile: schemas.EmployeeProfileRead) -> schemas.SmartRouteEmployee:
    photo_url = f"/attendance/persons/{profile.user_id}/photo" if profile.has_reference_image else None
    return schemas.SmartRouteEmployee(
        user_id=profile.user_id,
        created_at=profile.created_at,
        punch_count=profile.punch_count,
        has_reference_image=profile.has_reference_image,
        photo_url=photo_url,
        last_punch_at=profile.last_punch_at,
    )


def query_weather(question: str) -> str:
    """天气查询接口：从问题中识别城市并查询实时天气。"""
    city = extract_weather_city(question)
    weather = run_weather_tool(city)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"（{now}）调用了天气查询接口：{weather}"


def query_employee(question: str, db: Session) -> tuple[str, list[schemas.SmartRouteEmployee]]:
    """员工检索接口：返回打卡员工档案与头像地址。"""
    names = extract_employee_names(question)
    profiles = attendance_service.get_employee_profiles(db, names=names)
    employees = [_to_smart_route_employee(profile) for profile in profiles]

    if not employees:
        target = "、".join(names) if names else "已登记人员"
        return f"调用了员工知识库检索接口：未找到员工 {target}", []

    summaries = []
    for item in employees:
        punch_text = f"打卡 {item.punch_count} 次" if item.punch_count else "尚未打卡"
        summaries.append(f"{item.user_id}（{punch_text}）")
    message = f"调用了员工知识库检索接口：{'；'.join(summaries)}"
    return message, employees


def send_email(question: str) -> str:
    """邮件发送接口：解析收件人与正文并发送邮件。"""
    del question
    # TODO: 对接邮件服务（SMTP / 企业邮 API）
    raise NotImplementedError


def query_general(question: str) -> str:
    """通用问答接口：无法匹配具体业务时的兜底处理。"""
    del question
    # TODO: 转交通用对话或人工客服
    raise NotImplementedError
