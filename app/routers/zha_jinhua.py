from fastapi import APIRouter, Depends, HTTPException

from app import schemas
from app.core.permissions import is_super_admin, require_permission, user_permission_codes
from app.models import User
from app.services.zha_jinhua_service import get_engine

router = APIRouter(prefix="/game", tags=["zha-jinhua"])


@router.post("/start", response_model=schemas.ZhaJinhuaStartResponse)
def start_game(_: User = Depends(require_permission("89.start", name="开始一局"))) -> schemas.ZhaJinhuaStartResponse:
    result = get_engine().start_game()
    return schemas.ZhaJinhuaStartResponse(**result)


@router.post("/next-round", response_model=schemas.ZhaJinhuaStartResponse)
def next_round(_: User = Depends(require_permission("89.next-round", name="下一局"))) -> schemas.ZhaJinhuaStartResponse:
    result = get_engine().next_round()
    return schemas.ZhaJinhuaStartResponse(**result)


@router.post("/redeal", response_model=schemas.ZhaJinhuaStartResponse)
def redeal_round(
    body: schemas.ZhaJinhuaRedealRequest,
    user: User = Depends(require_permission("89.redeal", name="重新发牌")),
) -> schemas.ZhaJinhuaStartResponse:
    if body.mode != "random" and not (
        is_super_admin(user) or "89.access" in user_permission_codes(user)
    ):
        raise HTTPException(status_code=403, detail="只有管理员可以使用预设牌型")
    result = get_engine().redeal_round(body.mode)
    return schemas.ZhaJinhuaStartResponse(**result)


@router.post("/reset", response_model=schemas.ZhaJinhuaMessageResponse)
def reset_game(_: User = Depends(require_permission("89.reset", name="重置游戏"))) -> schemas.ZhaJinhuaMessageResponse:
    result = get_engine().reset_game()
    return schemas.ZhaJinhuaMessageResponse(**result)


@router.post("/turn/{player_id}", response_model=schemas.ZhaJinhuaTurnResponse)
async def player_turn(
    player_id: str,
    _: User = Depends(require_permission("89.turn", name="玩家出牌")),
) -> schemas.ZhaJinhuaTurnResponse:
    engine = get_engine()
    result = await engine.run_player_turn_async(player_id)
    return schemas.ZhaJinhuaTurnResponse(**result)


@router.get("/referee", response_model=schemas.ZhaJinhuaRefereeResponse)
async def get_referee_voice(
    _: User = Depends(require_permission("89.referee", name="裁判解说")),
) -> schemas.ZhaJinhuaRefereeResponse:
    commentary = await get_engine().run_referee_commentary_async()
    return schemas.ZhaJinhuaRefereeResponse(referee_voice=commentary)


@router.post("/access", response_model=schemas.ZhaJinhuaAccessResponse)
def set_game_access(
    body: schemas.ZhaJinhuaAccessRequest,
    _: User = Depends(require_permission("89.access", name="开启/关闭游戏")),
) -> schemas.ZhaJinhuaAccessResponse:
    result = get_engine().set_game_enabled(body.enabled)
    return schemas.ZhaJinhuaAccessResponse(**result)


@router.get("/status", response_model=schemas.ZhaJinhuaStatusResponse)
def get_status(_: User = Depends(require_permission("89.status", name="牌局状态"))) -> schemas.ZhaJinhuaStatusResponse:
    return schemas.ZhaJinhuaStatusResponse(**get_engine().public_status())
