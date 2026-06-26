from fastapi import APIRouter

from app import schemas
from app.services.agent_native import run_agent_native

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
def run_agent(body: schemas.AgentRunRequest) -> schemas.AgentRunResponse:
    question = body.question.strip()
    if body.engine == "langchain":
        from app.services.agent_langchain import run_agent_langchain

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
