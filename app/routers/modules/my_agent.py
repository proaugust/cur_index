from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.modules.agent_native import run_agent_native
from app.services.modules.rag_agentic_service import RagAgenticService

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


def _ok(question: str, engine: schemas.AgentEngine, result, *, mode=None) -> schemas.AgentRunResponse:
    steps, answer = result
    return schemas.AgentRunResponse(
        question=question,
        mode=mode,
        engine=engine,
        steps=_to_schema_steps(steps),
        answer=answer,
    )


@router.post("/run", response_model=schemas.AgentRunResponse, summary="原生 Agent")
def run_native(
    body: schemas.AgentNativeRunRequest,
    _: User = Depends(require_permission("84.run", name="运行 Agent")),
) -> schemas.AgentRunResponse:
    question = body.question.strip()
    return _ok(
        question,
        "native",
        run_agent_native(body.mode, question, temperature=body.temperature),
        mode=body.mode,
    )


@router.post("/langchain", response_model=schemas.AgentRunResponse, summary="LangChain LCEL 简单演示")
def run_langchain(
    body: schemas.AgentRunRequest,
    _: User = Depends(require_permission("84.langchain", name="LangChain Agent")),
) -> schemas.AgentRunResponse:
    from app.services.modules.agent_langchain import run_agent_langchain

    question = body.question.strip()
    return _ok(question, "langchain", run_agent_langchain(question, temperature=body.temperature))


@router.post("/autogen", response_model=schemas.AgentRunResponse, summary="AutoGen 简单演示")
def run_autogen(
    body: schemas.AgentRunRequest,
    _: User = Depends(require_permission("84.autogen", name="AutoGen Agent")),
) -> schemas.AgentRunResponse:
    from app.services.modules.agent_autogen import run_agent_autogen

    question = body.question.strip()
    return _ok(question, "autogen", run_agent_autogen(question, temperature=body.temperature))


@router.post("/crewai", response_model=schemas.AgentRunResponse, summary="CrewAI 简单演示")
def run_crewai(
    body: schemas.AgentRunRequest,
    _: User = Depends(require_permission("84.crewai", name="CrewAI Agent")),
) -> schemas.AgentRunResponse:
    from app.services.modules.agent_crewai import run_agent_crewai

    question = body.question.strip()
    return _ok(question, "crewai", run_agent_crewai(question, temperature=body.temperature))


@router.post("/agentic", response_model=schemas.AgentRunResponse, summary="多步 Agentic RAG")
def run_agentic(
    body: schemas.RagAgenticRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("84.agentic", name="多步 Agent")),
) -> schemas.AgentRunResponse:
    question = body.question.strip()
    return _ok(
        question,
        "agentic",
        RagAgenticService(db).run(
            body.corpus_name, question, per_step_limit=body.per_step_limit
        ),
    )
