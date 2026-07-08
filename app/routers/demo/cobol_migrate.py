from fastapi import APIRouter, Depends, HTTPException

from app import schemas
from app.core.permissions import require_permission
from app.models import User
from app.services.demo.cobol_migrate_demo import run_pipeline, run_step

router = APIRouter(prefix="/cobol_migrate", tags=["cobol_migrate"])


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


def _pack(step: int, step_name: str, agent_steps, payload: dict) -> schemas.CobolMigrateStepResponse:
    return schemas.CobolMigrateStepResponse(
        step=step,
        step_name=step_name,
        steps=_to_schema_steps(agent_steps),
        payload=payload,
    )


@router.post("/step/{step}", response_model=schemas.CobolMigrateStepResponse)
def run_migrate_step(
    step: int,
    _: User = Depends(require_permission("88.run", name="执行迁移步骤")),
) -> schemas.CobolMigrateStepResponse:
    try:
        packed = run_step(step)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _pack(*packed)


@router.post("/pipeline", response_model=schemas.CobolMigratePipelineResponse)
def run_migrate_pipeline(
    _: User = Depends(require_permission("88.pipeline", name="一键全流程")),
) -> schemas.CobolMigratePipelineResponse:
    results = [_pack(*item) for item in run_pipeline()]
    return schemas.CobolMigratePipelineResponse(results=results)
