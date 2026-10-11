from fastapi import APIRouter, Depends

from app import schemas
from app.core.permissions import require_permission
from app.models import User
from app.services.shared.llm import chat_completion

router = APIRouter(prefix="/chat", tags=["chat"])

_DEFAULT_SYSTEM = "你是一个 helpful 的 AI 助手，请用简洁清晰的中文回答用户问题。"


@router.post("/ask", response_model=schemas.ChatAskResponse)
def ask_chat(
    body: schemas.ChatAskRequest,
    _: User = Depends(require_permission("83.ask", name="AI 提问")),
) -> schemas.ChatAskResponse:
    system_prompt = body.system_prompt.strip() if body.system_prompt else _DEFAULT_SYSTEM
    history = [{"role": m.role, "content": m.content} for m in body.history]
    answer = chat_completion(
        system_prompt,
        body.question.strip(),
        history=history,
        temperature=body.temperature,
        caller="chat.ask",
    )
    return schemas.ChatAskResponse(question=body.question, answer=answer)
