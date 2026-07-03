"""炸金花 LLM 对局引擎。"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import re
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException

from app.game_logic.zha_jinhua import (
    build_pot_view,
    compare_two_players,
    evaluate_hand,
    format_cards,
    hand_label,
    judge_winner,
    shuffle_and_deal,
    stake_at_line_for,
)
from app.services.llm import chat_completion

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "routers" / "prompts"
ANTE = 5
MAX_RAISE = 100
INITIAL_BALANCE = 1000
MAX_ROUNDS = 10
MAX_ACTIONS_PER_ROUND = 24
MAX_RAISE_CYCLES = 3
MAX_RAISE_CYCLES_HEADS_UP = 2
MAX_BLIND_STALL_ACTIONS = 6

PLAYER_CONFIG: list[dict[str, str]] = [
    {"id": "Player_1", "role": "赌徒", "persona": "player1.md"},
    {"id": "Player_2", "role": "老炮", "persona": "player2.md"},
    {"id": "Player_3", "role": "数学家", "persona": "player3.md"},
]

VALID_ACTIONS = frozenset({"跟注", "加注", "比牌", "弃牌"})


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"提示词文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    candidates = [text]
    if text != raw.strip():
        candidates.append(raw.strip())
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        candidates.append(match.group())
    last_exc: json.JSONDecodeError | None = None
    for candidate in candidates:
        if not candidate.strip():
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_exc = exc
    logger.warning("炸金花 LLM 返回非 JSON: %s", raw[:300] if raw else "(empty)")
    detail = f"大模型返回非 JSON: {raw[:200]}" if raw else "大模型返回空内容，无法解析决策"
    raise HTTPException(status_code=502, detail=detail) from last_exc


def _actual_bet(amount: int, has_looked: bool) -> int:
    """明注面额 = 暗注标准×2（仅工具；发话扣款以 stake_at_line_for 为准，首发言明注除外）。"""
    return amount * 2 if has_looked else amount


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是"}
    return bool(value)


def _resolve_player_id(raw: str) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    for cfg in PLAYER_CONFIG:
        if text == cfg["id"] or text.startswith(cfg["id"]):
            return cfg["id"]
    return None


class ZhaJinhuaGameEngine:
    def __init__(self) -> None:
        self.player_template = _load_prompt("player_prompt.md")
        self.referee_template = _load_prompt("referee_prompt.md")
        self.personas = {p["id"]: _load_prompt(p["persona"]) for p in PLAYER_CONFIG}
        self.player_meta = {p["id"]: p for p in PLAYER_CONFIG}
        self.game_enabled = False
        self.game_state = self._fresh_state()

    def ensure_game_enabled(self) -> None:
        if not self.game_enabled:
            logger.warning("炸金花访问被拒: 游戏未开启")
            raise HTTPException(status_code=403, detail="游戏尚未开启，请联系管理员")

    def set_game_enabled(self, enabled: bool) -> dict[str, Any]:
        self.game_enabled = enabled
        logger.info("炸金花开关: enabled=%s", enabled)
        message = "游戏已开启，可以开始对局" if enabled else "游戏已关闭"
        return {"enabled": self.game_enabled, "message": message}

    def _fresh_state(self) -> dict[str, Any]:
        players: dict[str, dict[str, Any]] = {}
        for cfg in PLAYER_CONFIG:
            players[cfg["id"]] = {
                "balance": INITIAL_BALANCE,
                "cards": [],
                "has_looked": False,
                "alive": True,
                "all_in": False,
                "forced_all_in": False,
                "role": cfg["role"],
                "session_pnl": 0,
            }
        return {
            "round": 0,
            "max_rounds": MAX_ROUNDS,
            "pot": 0,
            "current_bet": ANTE,
            "phase": "idle",
            "action_logs": [],
            "thoughts": [],
            "players": players,
            "last_winner": None,
            "last_settlement": None,
            "turn_order": [p["id"] for p in PLAYER_CONFIG],
            "current_turn_idx": 0,
            "round_start_balances": {},
            "actions_this_round": 0,
            "pot_ledger": [],
            "pot_step": 0,
            "last_raiser": None,
            "pending_respondents": [],
            "raise_cycles_completed": 0,
            "blind_stall_actions": 0,
            "early_showdown": False,
            "last_actor_id": None,
            "last_actor_bet_blind": None,
            "awaiting_final_compare": False,
        }

    def _record_pot(
        self,
        player_id: str,
        amount: int,
        reason: str,
        *,
        always_log: bool = False,
        line_stake: int = 0,
    ) -> None:
        amount = int(amount)
        line_stake = int(line_stake or amount)
        if amount <= 0 and not always_log:
            return
        self.game_state["pot_step"] += 1
        self.game_state["pot_ledger"].append(
            {
                "step": self.game_state["pot_step"],
                "player_id": player_id,
                "display_name": self.display_name(player_id),
                "amount": amount,
                "reason": reason,
                "pot_after": int(self.game_state["pot"]),
                "line_stake": line_stake,
            }
        )

    def _stake_at_line_for(
        self,
        player_id: str,
        bet_line: int,
        *,
        compare_target_id: str | None = None,
        open_debut: bool = False,
        final_collect_compare: bool = False,
    ) -> int:
        """按发话规则计算本手线额（非累计抵扣）。"""
        info = self.game_state["players"][player_id]
        last_id = self.game_state.get("last_actor_id")
        prev = self.game_state["players"].get(last_id) if last_id else None
        has_prev = bool(
            last_id
            and prev is not None
            and prev["alive"]
        )
        target_blind = False
        if compare_target_id:
            target = self.game_state["players"].get(compare_target_id)
            if target and target["alive"]:
                target_blind = not target["has_looked"]
        return stake_at_line_for(
            bet_line,
            actor_has_looked=info["has_looked"],
            has_prev_actor=has_prev,
            compare_target_blind=target_blind,
            open_debut=open_debut,
            final_collect_compare=final_collect_compare,
        )

    def _action_stake_cost(
        self,
        player_id: str,
        bet_line: int,
        *,
        compare_target_id: str | None = None,
        charge_mode: Literal["gross", "raise_delta"] = "gross",
        open_debut: bool = False,
        final_collect_compare: bool = False,
    ) -> int:
        """本手应付：跟注/比牌=线额全额；加注=新旧注线下面额之差（不抵扣历史入池）。"""
        new_face = self._stake_at_line_for(
            player_id,
            bet_line,
            compare_target_id=compare_target_id,
            open_debut=open_debut,
            final_collect_compare=final_collect_compare,
        )
        if charge_mode == "raise_delta":
            current = self.game_state["current_bet"]
            old_face = self._stake_at_line_for(
                player_id,
                current,
                compare_target_id=compare_target_id,
                open_debut=False,
            )
            return max(0, new_face - old_face)
        return new_face

    def _charge_to_line(
        self,
        player_id: str,
        bet_line: int,
        reason: str,
        *,
        compare_target_id: str | None = None,
        charge_mode: Literal["gross", "raise_delta"] = "gross",
        open_debut: bool = False,
        final_collect_compare: bool = False,
    ) -> int:
        """扣款并入池；始终写一条 ledger（amount 为本次实际入池）。"""
        line_stake = self._stake_at_line_for(
            player_id,
            bet_line,
            compare_target_id=compare_target_id,
            open_debut=open_debut,
            final_collect_compare=final_collect_compare,
        )
        cost = self._action_stake_cost(
            player_id,
            bet_line,
            compare_target_id=compare_target_id,
            charge_mode=charge_mode,
            open_debut=open_debut,
            final_collect_compare=final_collect_compare,
        )
        paid = 0
        record_reason = reason
        if cost > 0:
            info = self.game_state["players"][player_id]
            if cost > info["balance"]:
                if info["balance"] <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{self.display_name(player_id)} 已无筹码",
                    )
                paid = info["balance"]
                info["balance"] = 0
                info["all_in"] = True
                info["forced_all_in"] = True
                self.game_state["pot"] += paid
                record_reason = f"{reason}/全下"
                self._mark_early_showdown(player_id)
            else:
                paid = cost
                info["balance"] -= paid
                self.game_state["pot"] += paid
        self._record_pot(
            player_id,
            paid,
            record_reason,
            always_log=True,
            line_stake=line_stake,
        )
        return paid

    def _set_raise_pending(self, raiser_id: str) -> None:
        alive = self._alive_players()
        self.game_state["last_raiser"] = raiser_id
        self.game_state["pending_respondents"] = [pid for pid in alive if pid != raiser_id]

    def _clear_player_pending(self, player_id: str) -> None:
        pending: list[str] = self.game_state["pending_respondents"]
        if player_id in pending:
            pending.remove(player_id)
        if not pending and self.game_state["last_raiser"]:
            self.game_state["raise_cycles_completed"] += 1

    def _all_alive_all_in(self) -> bool:
        alive = self._alive_players()
        return bool(alive) and all(self.game_state["players"][pid]["all_in"] for pid in alive)

    def _showdown_after_all_in_mix(self) -> bool:
        """至少一人全下且其余无人能继续加注时强制开牌。"""
        alive = self._alive_players()
        if len(alive) < 2:
            return False
        has_all_in = any(self.game_state["players"][pid]["all_in"] for pid in alive)
        if not has_all_in:
            return False
        can_bet = [
            pid
            for pid in alive
            if not self.game_state["players"][pid]["all_in"]
            and self.game_state["players"][pid]["balance"] > 0
        ]
        return len(can_bet) <= 1 and not self.game_state["pending_respondents"]

    def _mark_early_showdown(self, player_id: str) -> None:
        if self.game_state["early_showdown"]:
            return
        self.game_state["early_showdown"] = True
        note = (
            f"{self.display_name(player_id)} 筹码不足被动全下，"
            "本局禁止再加注，当前响应结束后提前开牌"
        )
        self.game_state["action_logs"].append(note)
        logger.info(
            "炸金花提前开牌标记 round=%s player=%s",
            self.game_state["round"],
            player_id,
        )

    def _all_alive_blind(self) -> bool:
        alive = self._alive_players()
        return bool(alive) and all(not self.game_state["players"][pid]["has_looked"] for pid in alive)

    def _raise_cycle_limit(self, alive_count: int) -> int | None:
        if alive_count >= 3:
            return MAX_RAISE_CYCLES
        if alive_count == 2:
            return MAX_RAISE_CYCLES_HEADS_UP
        return None

    def _track_blind_stall_after_action(self, action: str, looked_this_turn: bool) -> None:
        if looked_this_turn or action in {"弃牌", "比牌"}:
            self.game_state["blind_stall_actions"] = 0
            return
        alive = self._alive_players()
        if len(alive) >= 2 and action in {"跟注", "加注"} and self._all_alive_blind():
            self.game_state["blind_stall_actions"] += 1
        else:
            self.game_state["blind_stall_actions"] = 0

    def _force_showdown(self, reason: str) -> None:
        alive = self._alive_players()
        if len(alive) <= 1:
            if alive:
                self._settle_round(alive[0])
            return
        hands = {pid: self.game_state["players"][pid]["cards"] for pid in alive}
        winner_id = judge_winner(hands)
        for pid in alive:
            cards = self.game_state["players"][pid]["cards"]
            self.game_state["action_logs"].append(
                f"{self.display_name(pid)} 亮牌: {format_cards(cards)}({hand_label(cards)})"
            )
        self.game_state["action_logs"].append(reason)
        self._record_pot(winner_id, 0, "开牌", always_log=True)
        self._settle_round(winner_id)

    def _check_force_showdown(self) -> bool:
        if self.game_state["phase"] != "betting":
            return False
        alive = self._alive_players()
        if len(alive) <= 1:
            return False
        if (
            self.game_state["early_showdown"]
            and not self.game_state["pending_respondents"]
        ):
            self._force_showdown("有人筹码不足全下，提前开牌结算")
            return True
        if self.game_state["actions_this_round"] >= MAX_ACTIONS_PER_ROUND:
            self._force_showdown("本局行动次数达上限，强制开牌结算")
            return True
        if self._all_alive_all_in():
            self._force_showdown("全员已全下，强制开牌结算")
            return True
        if self._showdown_after_all_in_mix():
            self._force_showdown("存在全下且无人能继续加注，强制开牌结算")
            return True
        cycle_limit = self._raise_cycle_limit(len(alive))
        if (
            cycle_limit is not None
            and self.game_state["raise_cycles_completed"] >= cycle_limit
        ):
            label = "两人" if len(alive) == 2 else "三人"
            self._force_showdown(
                f"{label}僵持达 {cycle_limit} 轮加注周期，强制开牌结算"
            )
            return True
        if (
            len(alive) == 2
            and self._all_alive_blind()
            and self.game_state["blind_stall_actions"] >= MAX_BLIND_STALL_ACTIONS
        ):
            self._force_showdown(
                f"两人闷牌互顶达 {MAX_BLIND_STALL_ACTIONS} 手，强制开牌结算"
            )
            return True
        return False

    def _apply_look(self, player_id: str, look: bool) -> str:
        if not look:
            return ""
        info = self.game_state["players"][player_id]
        if info["has_looked"]:
            return ""
        info["has_looked"] = True
        return f"{self.display_name(player_id)} 选择 [看牌]，手牌: {format_cards(info['cards'])}"

    def _validate_action(self, player_id: str, action: str) -> None:
        alive = self._alive_players()
        if action == "比牌":
            if len(alive) < 2:
                raise HTTPException(status_code=400, detail="至少两名玩家在场时才能比牌")
        if action == "加注":
            if self.game_state["early_showdown"]:
                raise HTTPException(
                    status_code=400,
                    detail="有人已筹码不足全下，本局禁止再加注",
                )
            pending: list[str] = self.game_state["pending_respondents"]
            if pending and player_id not in pending:
                raise HTTPException(status_code=400, detail="尚有玩家未响应上一手加注，你不能加注")

    def display_name(self, player_id: str) -> str:
        meta = self.player_meta[player_id]
        return f"{player_id}（{meta['role']}）"

    def _alive_players(self) -> list[str]:
        return [pid for pid in self.game_state["turn_order"] if self.game_state["players"][pid]["alive"]]

    def current_player_id(self) -> str | None:
        alive = self._alive_players()
        if not alive or self.game_state["phase"] != "betting":
            return None
        idx = self.game_state["current_turn_idx"] % len(self.game_state["turn_order"])
        for offset in range(len(self.game_state["turn_order"])):
            pid = self.game_state["turn_order"][(idx + offset) % len(self.game_state["turn_order"])]
            if self.game_state["players"][pid]["alive"]:
                return pid
        return None

    def _advance_turn(self) -> None:
        n = len(self.game_state["turn_order"])
        self.game_state["current_turn_idx"] = (self.game_state["current_turn_idx"] + 1) % n

    def get_other_players_status(self, current_player: str) -> str:
        parts: list[str] = []
        for pid, info in self.game_state["players"].items():
            if pid == current_player:
                continue
            alive = "存活" if info["alive"] else "已弃牌"
            looked = "已看牌" if info["has_looked"] else "未看牌"
            parts.append(f"{self.display_name(pid)}({alive}, {looked})")
        return ", ".join(parts)

    def _begin_round(self) -> dict[str, Any]:
        if self.game_state["round"] >= MAX_ROUNDS and self.game_state["phase"] == "ended":
            raise HTTPException(status_code=400, detail="已完成 10 局，请重置后再开")

        self.game_state["round"] += 1
        player_ids = [p["id"] for p in PLAYER_CONFIG]
        dealt = shuffle_and_deal(player_ids)
        self.game_state["round_start_balances"] = {}

        for pid in player_ids:
            p = self.game_state["players"][pid]
            self.game_state["round_start_balances"][pid] = p["balance"]
            p["cards"] = dealt[pid]
            p["has_looked"] = False
            p["alive"] = True
            p["all_in"] = False
            p["forced_all_in"] = False
            p["balance"] -= ANTE

        self.game_state["pot"] = 0
        self.game_state["current_bet"] = ANTE
        self.game_state["action_logs"] = []
        self.game_state["thoughts"] = []
        self.game_state["last_winner"] = None
        self.game_state["last_settlement"] = None
        self.game_state["current_turn_idx"] = 0
        self.game_state["actions_this_round"] = 0
        self.game_state["pot_ledger"] = []
        self.game_state["pot_step"] = 0
        self.game_state["last_raiser"] = None
        self.game_state["pending_respondents"] = []
        self.game_state["raise_cycles_completed"] = 0
        self.game_state["blind_stall_actions"] = 0
        self.game_state["early_showdown"] = False
        self.game_state["last_actor_id"] = None
        self.game_state["last_actor_bet_blind"] = None
        self.game_state["awaiting_final_compare"] = False

        for pid in player_ids:
            self.game_state["pot"] += ANTE
            self._record_pot(pid, ANTE, "底分")

        # 底分写入 ledger 后再暴露 betting，避免 GET /status 看到空明细
        self.game_state["phase"] = "betting"

        logger.info(
            "炸金花开局 round=%s pot=%s phase=%s",
            self.game_state["round"],
            self.game_state["pot"],
            self.game_state["phase"],
        )
        return {
            "message": f"第 {self.game_state['round']} 局开始，已发牌并扣除底分 {ANTE} 元",
            "state": self.public_status(),
        }

    def start_game(self) -> dict[str, Any]:
        self.ensure_game_enabled()
        if self.game_state["phase"] not in {"idle"}:
            raise HTTPException(status_code=400, detail="游戏已开始，请用「下一局」或「重置」")
        return self._begin_round()

    def next_round(self) -> dict[str, Any]:
        self.ensure_game_enabled()
        if self.game_state["phase"] != "round_end":
            raise HTTPException(status_code=400, detail="当前局尚未结束，无法开始下一局")
        if self.game_state["round"] >= MAX_ROUNDS:
            raise HTTPException(status_code=400, detail="已完成全部 10 局")
        return self._begin_round()

    def reset_game(self) -> dict[str, str]:
        self.game_state = self._fresh_state()
        logger.info("炸金花已重置")
        return {"message": "游戏已重置"}

    def _build_player_prompt(self, player_id: str) -> str:
        info = self.game_state["players"][player_id]
        opponents = [
            self.display_name(pid)
            for pid in self._alive_players()
            if pid != player_id
        ]
        alive = self._alive_players()
        heads_up_hint = ""
        if len(alive) == 2:
            heads_up_hint = (
                "【只剩两人】应优先 look:true 后比牌抓诈，或弃牌止损；"
                "勿无限闷牌跟注/加注，僵持过久系统将强制开牌。"
            )
        early_showdown_note = ""
        if self.game_state["early_showdown"]:
            early_showdown_note = (
                "【提前开牌】有人筹码不足已全下：本局禁止再加注，"
                "仅可跟注/弃牌/（两人时）比牌；本轮响应结束后将开牌。"
            )
        return self.player_template.format(
            persona_description=self.personas[player_id].strip(),
            player_name=self.display_name(player_id),
            balance=info["balance"],
            cards=",".join(info["cards"]) if info["has_looked"] else "未看牌（不可见）",
            has_looked="是" if info["has_looked"] else "否",
            pot=self.game_state["pot"],
            current_bet=self.game_state["current_bet"],
            other_players_status=self.get_other_players_status(player_id),
            alive_opponents="、".join(opponents) if opponents else "无",
            alive_count=len(alive),
            heads_up_hint=heads_up_hint,
            early_showdown_note=early_showdown_note,
        )

    def run_player_turn(self, player_id: str | None = None) -> dict[str, Any]:
        self.ensure_game_enabled()
        if self.game_state["phase"] != "betting":
            raise HTTPException(status_code=400, detail="当前不在下注阶段")

        expected = self.current_player_id()
        if player_id is None:
            player_id = expected
        if player_id is None:
            raise HTTPException(status_code=400, detail="无可用玩家")
        if expected and player_id != expected:
            raise HTTPException(
                status_code=400,
                detail=f"尚未轮到 {player_id}，当前应为 {expected}",
            )

        if player_id not in self.game_state["players"]:
            raise HTTPException(status_code=404, detail="玩家不存在")

        info = self.game_state["players"][player_id]
        if not info["alive"]:
            return self._turn_response(player_id, skipped=True, reason="已弃牌")

        if info["all_in"]:
            self._advance_turn()
            if len(self._alive_players()) == 1:
                self._settle_round(self._alive_players()[0])
            elif self._check_force_showdown():
                pass
            return self._turn_response(player_id, skipped=True, reason="已全下，跳过行动")

        if self.game_state["actions_this_round"] >= MAX_ACTIONS_PER_ROUND:
            self._force_showdown("本局行动次数达上限，强制开牌结算")
            return self._turn_response(player_id, skipped=True, reason="本局行动次数达上限，强制开牌结算")

        system_prompt = self._build_player_prompt(player_id)
        logger.info(
            "炸金花出牌开始 round=%s player=%s pot=%s current_bet=%s",
            self.game_state["round"],
            player_id,
            self.game_state["pot"],
            self.game_state["current_bet"],
        )

        decision = self._request_player_decision(player_id, system_prompt)
        if decision is None:
            return self._llm_fallback_turn(player_id)

        thought = str(decision.get("thought", "")).strip()
        action = str(decision.get("action", "")).strip()
        look = _parse_bool(decision.get("look", False))
        amount = int(decision.get("amount") or 0)
        target_raw = str(decision.get("target", "")).strip()

        if action == "看牌":
            return self._llm_fallback_turn(player_id)
        if action not in VALID_ACTIONS:
            logger.warning(
                "炸金花非法 action round=%s player=%s action=%s",
                self.game_state["round"],
                player_id,
                action,
            )
            return self._llm_fallback_turn(player_id)
        if action == "加注" and self.game_state["early_showdown"]:
            action = "跟注"
            amount = 0

        return self._finalize_player_turn(
            player_id,
            thought=thought,
            action=action,
            amount=amount,
            target_raw=target_raw,
            look=look,
        )

    def _request_player_decision(self, player_id: str, system_prompt: str) -> dict[str, Any] | None:
        user_msg = "请根据当前局势做出你的下一步决策，严格输出 JSON。"
        attempts: list[tuple[str, bool, bool]] = [
            ("zha_jinhua.player_turn", True, True),
            ("zha_jinhua.player_turn.retry", False, True),
        ]
        for caller, json_mode, disable_thinking in attempts:
            try:
                raw = chat_completion(
                    system_prompt,
                    user_msg,
                    temperature=0.5,
                    json_mode=json_mode,
                    disable_thinking=disable_thinking,
                    caller=caller,
                )
                return _parse_llm_json(raw)
            except HTTPException as exc:
                if exc.status_code != 502:
                    raise
                logger.info(
                    "炸金花 LLM 尝试失败 caller=%s round=%s player=%s detail=%s",
                    caller,
                    self.game_state["round"],
                    player_id,
                    exc.detail,
                )
        return None

    def _is_fallback_hand_good(self, cards: list[str]) -> bool:
        """代打牌力：至少对子才算还可以。"""
        return evaluate_hand(cards)[2] != "high_card"

    def _llm_fallback_turn(self, player_id: str) -> dict[str, Any]:
        """LLM 全部失败时按牌力规则兜底，避免局内冻住。"""
        info = self.game_state["players"][player_id]
        cards = info["cards"]
        label = hand_label(cards)
        alive = self._alive_players()
        amount = 0
        target_raw = ""

        if info["balance"] <= 0 and not info["all_in"]:
            action, look, thought = "弃牌", False, "模型不可用，无力跟注，系统代为弃牌"
        elif not self._is_fallback_hand_good(cards):
            action, look, thought = "弃牌", False, f"模型不可用，{label}偏弱，系统代为弃牌"
        elif len(alive) == 2:
            others = [pid for pid in alive if pid != player_id]
            target_raw = others[0] if others else ""
            action, look, thought = "比牌", True, f"模型不可用，{label}尚可，系统代为看牌比牌"
        else:
            action, look, thought = "跟注", False, f"模型不可用，{label}尚可，三人局系统代为跟注"

        self.game_state["action_logs"].append(
            f"{self.display_name(player_id)} [系统兜底] {action}（大模型无有效响应）"
        )
        logger.warning(
            "炸金花 LLM 兜底出牌 round=%s player=%s hand=%s action=%s target=%s",
            self.game_state["round"],
            player_id,
            label,
            action,
            target_raw or None,
        )
        try:
            return self._finalize_player_turn(
                player_id,
                thought=thought,
                action=action,
                amount=amount,
                target_raw=target_raw,
                look=look,
            )
        except HTTPException:
            if action != "比牌":
                raise
            logger.warning(
                "炸金花兜底比牌失败，降级跟注 round=%s player=%s",
                self.game_state["round"],
                player_id,
            )
            self.game_state["action_logs"].append(
                f"{self.display_name(player_id)} [系统兜底] 比牌不可用，改为跟注"
            )
            return self._finalize_player_turn(
                player_id,
                thought=f"模型不可用，{label}尚可，比牌失败改为跟注",
                action="跟注",
                amount=0,
                target_raw="",
                look=False,
            )

    def _finalize_player_turn(
        self,
        player_id: str,
        *,
        thought: str,
        action: str,
        amount: int,
        target_raw: str,
        look: bool,
    ) -> dict[str, Any]:
        self._validate_action(player_id, action)
        action_meta = self._apply_action(player_id, action, amount, thought, target_raw, look=look)
        self.game_state["actions_this_round"] += 1
        self._advance_turn()

        alive = self._alive_players()
        if len(alive) == 1:
            self.game_state["awaiting_final_compare"] = False
            self._settle_round(alive[0])
        else:
            self._check_force_showdown()

        logger.info(
            "炸金花出牌完成 round=%s player=%s action=%s cost=%s target=%s phase=%s",
            self.game_state["round"],
            player_id,
            action,
            action_meta["cost"],
            target_raw or None,
            self.game_state["phase"],
        )
        return self._turn_response(
            player_id,
            thought=thought,
            action=action,
            amount=action_meta["cost"],
            bet_tag=action_meta["bet_tag"],
            target=target_raw,
        )

    def _turn_response(
        self,
        player_id: str,
        *,
        skipped: bool = False,
        reason: str = "",
        thought: str = "",
        action: str = "",
        amount: int = 0,
        bet_tag: str = "",
        target: str = "",
    ) -> dict[str, Any]:
        return {
            "player_id": player_id,
            "display_name": self.display_name(player_id),
            "skipped": skipped,
            "reason": reason,
            "thought": thought,
            "action": action,
            "amount": amount,
            "bet_tag": bet_tag,
            "target": target,
            "state": self.public_status(),
        }

    def _apply_action(
        self,
        player_id: str,
        action: str,
        amount: int,
        thought: str,
        target_raw: str,
        *,
        look: bool = False,
    ) -> dict[str, Any]:
        info = self.game_state["players"][player_id]
        log_lines: list[str] = []
        cost = 0
        bet_tag = ""

        look_line = self._apply_look(player_id, look)
        if look_line:
            log_lines.append(look_line)

        if action == "弃牌":
            info["alive"] = False
            self._clear_player_pending(player_id)
            self._record_pot(player_id, 0, "弃牌", always_log=True)
            log_lines.append(f"{self.display_name(player_id)} 选择 [弃牌]")
        elif action == "跟注":
            bet = self.game_state["current_bet"]
            bet_tag = "明注" if info["has_looked"] else "暗注"
            cost = self._charge_to_line(
                player_id, bet, f"跟注/{bet_tag}", open_debut=bool(look)
            )
            self._clear_player_pending(player_id)
            suffix = "（全下）" if info["all_in"] else ""
            log_lines.append(
                f"{self.display_name(player_id)} 选择 [跟注/{bet_tag}], 筹码变动: {cost}元{suffix}"
            )
        elif action == "加注":
            raise_line = amount
            if raise_line <= self.game_state["current_bet"]:
                raise_line = self.game_state["current_bet"] + 10
            if raise_line > MAX_RAISE:
                raise_line = MAX_RAISE
            bet_tag = "明注" if info["has_looked"] else "暗注"
            cost = self._charge_to_line(
                player_id,
                raise_line,
                f"加注/{bet_tag}",
                charge_mode="raise_delta",
                open_debut=bool(look),
            )
            self.game_state["current_bet"] = raise_line
            self._set_raise_pending(player_id)
            suffix = "（全下）" if info["all_in"] else ""
            log_lines.append(
                f"{self.display_name(player_id)} 选择 [加注/{bet_tag}], 加注线: {raise_line}元, 筹码变动: {cost}元{suffix}"
            )
        elif action == "比牌":
            target_id = _resolve_player_id(target_raw)
            if not target_id or target_id == player_id:
                alive_others = [p for p in self._alive_players() if p != player_id]
                if not alive_others:
                    raise HTTPException(status_code=400, detail="无可比牌对象")
                target_id = alive_others[0]
            cost = self._do_compare(player_id, target_id)
            self._clear_player_pending(player_id)

        self._track_blind_stall_after_action(action, looked_this_turn=bool(look_line))
        if action in {"跟注", "加注", "比牌"}:
            self.game_state["last_actor_id"] = player_id
            self.game_state["last_actor_bet_blind"] = not info["has_looked"]

        if thought:
            self.game_state["thoughts"].append(f"{self.display_name(player_id)}: {thought}")
        self.game_state["action_logs"].extend(log_lines)
        return {"cost": cost, "bet_tag": bet_tag}

    def _do_compare(self, challenger_id: str, target_id: str) -> int:
        challenger = self.game_state["players"][challenger_id]
        target = self.game_state["players"][target_id]
        if not target["alive"]:
            raise HTTPException(status_code=400, detail="比牌目标已弃牌")
        compare_reason = "比牌/明注" if challenger["has_looked"] else "比牌"
        compare_fee = self._charge_to_line(
            challenger_id,
            self.game_state["current_bet"],
            compare_reason,
            compare_target_id=target_id,
        )

        cmp = compare_two_players(challenger["cards"], target["cards"])
        tie_note = ""
        if cmp > 0:
            loser_id = target_id
            winner_id = challenger_id
        elif cmp < 0:
            loser_id = challenger_id
            winner_id = target_id
        else:
            loser_id = challenger_id
            winner_id = target_id
            tie_note = "（同牌同点，比牌发起者出局）"

        self.game_state["players"][loser_id]["alive"] = False
        self._clear_player_pending(loser_id)
        c_label = hand_label(challenger["cards"])
        t_label = hand_label(target["cards"])
        self.game_state["action_logs"].append(
            f"{self.display_name(challenger_id)} 与 {self.display_name(target_id)} [比牌]: "
            f"{format_cards(challenger['cards'])}({c_label}) vs "
            f"{format_cards(target['cards'])}({t_label}) → "
            f"{self.display_name(winner_id)} 胜，{self.display_name(loser_id)} 出局{tie_note}"
        )
        return compare_fee

    def _build_settlement(
        self,
        winner_id: str,
        pot: int,
        pot_ledger: list[dict[str, Any]],
    ) -> dict[str, Any]:
        pot_total = sum(int(entry["amount"]) for entry in pot_ledger)
        winner_contribution = sum(
            int(entry["amount"]) for entry in pot_ledger if entry["player_id"] == winner_id
        )
        winner_net_win = max(pot_total - winner_contribution, 0)
        details: dict[str, Any] = {}
        for pid, info in self.game_state["players"].items():
            start = self.game_state["round_start_balances"].get(pid, info["balance"])
            round_pnl = info["balance"] - start
            info["session_pnl"] = info["balance"] - INITIAL_BALANCE
            details[pid] = {
                "display_name": self.display_name(pid),
                "cards": info["cards"],
                "cards_display": format_cards(info["cards"]),
                "hand_label": hand_label(info["cards"]),
                "round_pnl": round_pnl,
                "balance": info["balance"],
                "session_pnl": info["session_pnl"],
                "alive": info["alive"],
            }
        return {
            "winner_id": winner_id,
            "winner_name": self.display_name(winner_id),
            "pot_total": pot_total,
            "winner_net_win": winner_net_win,
            "pot_ledger": list(pot_ledger),
            "players": details,
        }

    def _settle_round(self, winner_id: str) -> None:
        winner = self.game_state["players"][winner_id]
        pot = self.game_state["pot"]
        ledger_snapshot = list(self.game_state["pot_ledger"])
        if pot > 0:
            winner["balance"] += pot
        self.game_state["pot"] = 0
        # pot_ledger 保留至下一局 _begin_round 再清空，供局末继续展示
        self.game_state["last_winner"] = winner_id
        settlement = self._build_settlement(winner_id, pot, ledger_snapshot)
        self.game_state["last_settlement"] = settlement
        if self.game_state["round"] >= MAX_ROUNDS:
            self.game_state["phase"] = "ended"
        else:
            self.game_state["phase"] = "round_end"
        net_win = settlement["winner_net_win"]
        self.game_state["action_logs"].append(
            f"本局结束，{self.display_name(winner_id)} 从对手处净赢 {net_win} 元"
            f"（池内共 {pot} 元，含自身投入 {settlement['pot_total'] - net_win} 元）"
        )
        logger.info(
            "炸金花局结算 round=%s winner=%s pot=%s phase=%s",
            self.game_state["round"],
            winner_id,
            pot,
            self.game_state["phase"],
        )

    def run_referee_commentary(self) -> str:
        self.ensure_game_enabled()
        if not self.game_state["action_logs"] and not self.game_state["thoughts"]:
            return "本局尚无行动，请先让玩家们出牌。"

        referee_prompt = self.referee_template.format(
            action_logs="\n".join(self.game_state["action_logs"]),
            player_thoughts="\n".join(self.game_state["thoughts"]) or "（暂无）",
        )
        return chat_completion(
            referee_prompt,
            "请给出本轮精彩解说。",
            temperature=0.9,
            caller="zha_jinhua.referee",
        ).strip()

    def public_status(self) -> dict[str, Any]:
        phase = self.game_state["phase"]
        is_betting = phase == "betting"
        show_pot_ledger = phase in ("betting", "round_end", "ended")
        player_ids = [p["id"] for p in PLAYER_CONFIG]
        display_names = {pid: self.display_name(pid) for pid in player_ids}
        players: dict[str, Any] = {}
        for pid, info in self.game_state["players"].items():
            cards = info["cards"]
            players[pid] = {
                "display_name": self.display_name(pid),
                "balance": info["balance"],
                "has_looked": info["has_looked"],
                "alive": info["alive"],
                "all_in": info["all_in"],
                "forced_all_in": info.get("forced_all_in", False),
                "cards": cards,
                "cards_display": format_cards(cards) if cards else "",
                "hand_label": hand_label(cards) if cards else "",
                "session_pnl": info["balance"] - INITIAL_BALANCE,
            }
        ledger = list(self.game_state["pot_ledger"]) if show_pot_ledger else []
        pot_view = (
            build_pot_view(ledger, player_ids, display_names)
            if show_pot_ledger
            else None
        )
        return {
            "round": self.game_state["round"],
            "max_rounds": self.game_state["max_rounds"],
            "pot": self.game_state["pot"] if is_betting else 0,
            "current_bet": self.game_state["current_bet"] if is_betting else 0,
            "phase": phase,
            "early_showdown": self.game_state["early_showdown"] if is_betting else False,
            "game_enabled": self.game_enabled,
            "last_winner": self.game_state["last_winner"],
            "last_winner_name": (
                self.display_name(self.game_state["last_winner"])
                if self.game_state["last_winner"]
                else None
            ),
            "current_player_id": self.current_player_id() if is_betting else None,
            "actions_this_round": self.game_state["actions_this_round"] if is_betting else 0,
            "max_actions_per_round": MAX_ACTIONS_PER_ROUND,
            "last_settlement": self.game_state["last_settlement"],
            "pot_ledger": ledger,
            "pot_view": pot_view,
            "players": players,
        }

    async def run_player_turn_async(self, player_id: str | None = None) -> dict[str, Any]:
        ctx = contextvars.copy_context()
        return await asyncio.to_thread(ctx.run, self.run_player_turn, player_id)

    async def run_referee_commentary_async(self) -> str:
        ctx = contextvars.copy_context()
        return await asyncio.to_thread(ctx.run, self.run_referee_commentary)


_engine: ZhaJinhuaGameEngine | None = None


def get_engine() -> ZhaJinhuaGameEngine:
    global _engine
    if _engine is None:
        _engine = ZhaJinhuaGameEngine()
    return _engine
