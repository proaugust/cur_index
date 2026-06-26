from fastapi import APIRouter

from app import schemas
from app.services.llm import chat_completion

router = APIRouter(prefix="/meeting", tags=["meeting"])

_SYSTEM_PROMPT = (
    "你是专业的会议纪要整理助手。用户会提供一段杂乱、口语化或未经整理的会议记录。"
    "请将其整理为条理清晰、结论明确的会议纪要，使用 Markdown 格式输出。\n"
    "要求：\n"
    "1. 先写一段简要总结（1～3 句，概括会议主题与核心结论）；\n"
    "2. 按议题或主题分节，每节列出讨论要点；\n"
    "3. 单独列出「决议 / 结论」；\n"
    "4. 如有待办，列出「待办事项」（负责人、事项、截止时间若原文有则保留，无则标「待定」）；\n"
    "5. 仅基于原文信息整理，不编造内容；原文缺失的信息可标注「原文未提及」。"
)


@router.post("/organize", response_model=schemas.MeetingOrganizeResponse)
def organize_meeting(body: schemas.MeetingOrganizeRequest) -> schemas.MeetingOrganizeResponse:
    text = body.text.strip()
    user_prompt = f"请整理以下会议记录：\n\n{text}"
    organized = chat_completion(_SYSTEM_PROMPT, user_prompt, temperature=body.temperature)
    return schemas.MeetingOrganizeResponse(original_text=text, organized_text=organized)
