from fastapi import APIRouter, Depends

from app import schemas
from app.core.permissions import require_permission
from app.models import User
from app.services.demo.agent_native import run_agent_native

router = APIRouter(prefix="/my_agent", tags=["my_agent"])


def _to_schema_steps(steps) -> list[schemas.AgentStep]:
    return [
        schemas.AgentStep(
            agent=s.agent,
            role=s.role,
            input=s.input,
            output=s.output,
            status=s.status,
            meta=s.meta,
        )
        for s in steps
    ]


@router.post("/run", response_model=schemas.AgentRunResponse)
def run_agent(
    body: schemas.AgentRunRequest,
    _: User = Depends(require_permission("84.run", name="运行 Agent")),
) -> schemas.AgentRunResponse:
    question = body.question.strip()
    if body.engine == "langchain":
        from app.services.demo.agent_langchain import run_agent_langchain

        steps, answer = run_agent_langchain(body.mode, question, temperature=body.temperature)
    else:
        steps, answer = run_agent_native(body.mode, question, temperature=body.temperature)

    return schemas.AgentRunResponse(
        question=question,
        mode=body.mode,
        engine=body.engine,
        steps=_to_schema_steps(steps),
        answer=answer,
    )
