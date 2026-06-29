from fastapi import APIRouter, Depends

from app import schemas
from app.core.permissions import require_permission
from app.models import User
from app.services.llm import chat_completion

router = APIRouter(prefix="/chat", tags=["chat"])

_DEFAULT_SYSTEM = "你是一个 helpful 的 AI 助手，请用简洁清晰的中文回答用户问题。"


def _build_user_prompt(question: str, history: list[schemas.ChatMessage]) -> str:
    if not history:
        return question
    lines: list[str] = []
    for msg in history:
        role = "用户" if msg.role == "user" else "助手"
        lines.append(f"{role}：{msg.content}")
    lines.append(f"用户：{question}")
    return "\n".join(lines)


@router.post("/ask", response_model=schemas.ChatAskResponse)
def ask_chat(
    body: schemas.ChatAskRequest,
    _: User = Depends(require_permission("83.ask")),
) -> schemas.ChatAskResponse:

    system_prompt = body.system_prompt.strip() if body.system_prompt else _DEFAULT_SYSTEM
    user_prompt = _build_user_prompt(body.question.strip(), body.history)
    answer = chat_completion(system_prompt, user_prompt, temperature=body.temperature)
    return schemas.ChatAskResponse(question=body.question, answer=answer)
