import json
import logging
import re

from app.core.config import settings
from app.services.demo.complaint_categories import CATEGORY_SEEDS
from app.services.shared.llm import chat_completion

logger = logging.getLogger(__name__)

_SYSTEM = """你是电信投诉分类助手。根据用户投诉内容，生成一个简短的投诉类型名称和一句描述。
命名规则：
- 类型名 4～12 个汉字，名词短语，不要标点
- 风格参考：网络与信号质量、售后与维保服务、资费与账单争议
- 只输出 JSON：{"name": "...", "description": "..."}"""


def _sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", value.strip())
    return cleaned[:20]


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _fallback_name(complaint_text: str) -> str:
    compact = re.sub(r"\s+", "", complaint_text.strip())
    if len(compact) >= 4:
        return compact[:10]
    return "其他投诉"


def suggest_complaint_category(complaint_text: str, *, existing_names: list[str]) -> tuple[str, str]:
    examples = "、".join(list(CATEGORY_SEEDS.keys())[:5])
    existing = "、".join(existing_names[:12]) if existing_names else "无"
    user_prompt = (
        f"已有类型：{existing}\n\n"
        f"投诉内容：\n{complaint_text}\n\n"
        f"请生成与已有类型不重复的新类型名。命名风格参考：{examples}"
    )

    if settings.openai_api_key:
        try:
            raw = chat_completion(_SYSTEM, user_prompt, temperature=0.2, caller="complaint.category_namer")
            parsed = _parse_json(raw)
            name = _sanitize_name(str(parsed.get("name", "")))
            description = str(parsed.get("description", "")).strip() or complaint_text[:120]
            if len(name) >= 2:
                return name, description
        except Exception:
            logger.warning("LLM 投诉分类命名失败，使用降级策略", exc_info=True)

    return _fallback_name(complaint_text), complaint_text[:120]
