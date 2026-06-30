"""炸金花 LLM 对局引擎。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.game_logic.zha_jinhua import (
    compare_two_players,
    format_cards,
    hand_label,
    judge_winner,
    shuffle_and_deal,
)
from app.services.llm import chat_completion

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "routers" / "prompts"
ANTE = 5
MAX_RAISE = 100
INITIAL_BALANCE = 1000
MAX_ROUNDS = 10
MAX_ACTIONS_PER_ROUND = 24

PLAYER_CONFIG: list[dict[str, str]] = [
    {"id": "Player_1", "role": "赌徒", "persona": "player1.md"},
    {"id": "Player_2", "role": "老炮", "persona": "player2.md"},
    {"id": "Player_3", "role": "数学家", "persona": "player3.md"},
]

VALID_ACTIONS = frozenset({"看牌", "跟注", "加注", "比牌", "弃牌"})


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
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"大模型返回非 JSON: {raw[:200]}") from exc


def _actual_bet(amount: int, has_looked: bool) -> int:
    """暗注=amount；明注=amount×2。"""
    return amount * 2 if has_looked else amount


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
            raise HTTPException(status_code=403, detail="游戏尚未开启，请联系管理员")

    def set_game_enabled(self, enabled: bool) -> dict[str, Any]:
        self.game_enabled = enabled
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
        }

    def _record_pot(self, player_id: str, amount: int, reason: str) -> None:
        if amount <= 0:
            return
        self.game_state["pot_step"] += 1
        self.game_state["pot_ledger"].append(
            {
                "step": self.game_state["pot_step"],
                "player_id": player_id,
                "display_name": self.display_name(player_id),
                "amount": amount,
                "reason": reason,
            }
        )

    def _player_pot_contribution(self, player_id: str) -> int:
        return sum(
            entry["amount"]
            for entry in self.game_state["pot_ledger"]
            if entry["player_id"] == player_id
        )

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
            p["balance"] -= ANTE

        self.game_state["pot"] = ANTE * len(player_ids)
        self.game_state["current_bet"] = ANTE
        self.game_state["phase"] = "betting"
        self.game_state["action_logs"] = []
        self.game_state["thoughts"] = []
        self.game_state["last_winner"] = None
        self.game_state["last_settlement"] = None
        self.game_state["current_turn_idx"] = 0
        self.game_state["actions_this_round"] = 0
        self.game_state["pot_ledger"] = []
        self.game_state["pot_step"] = 0

        for pid in player_ids:
            self._record_pot(pid, ANTE, "底分")

        return {
            "message": f"第 {self.game_state['round']} 局开始，已发牌并扣除底分 {ANTE} 元",
            "round": self.game_state["round"],
            "pot": self.game_state["pot"],
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
        return {"message": "游戏已重置"}

    def _build_player_prompt(self, player_id: str) -> str:
        info = self.game_state["players"][player_id]
        opponents = [
            self.display_name(pid)
            for pid in self._alive_players()
            if pid != player_id
        ]
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

        if self.game_state["actions_this_round"] >= MAX_ACTIONS_PER_ROUND:
            alive = self._alive_players()
            self._settle_round(judge_winner({p: self.game_state["players"][p]["cards"] for p in alive}))
            return self._turn_response(player_id, skipped=True, reason="本局行动次数达上限，强制开牌结算")

        system_prompt = self._build_player_prompt(player_id)
        try:
            raw = chat_completion(
                system_prompt,
                "请根据当前局势做出你的下一步决策，严格输出 JSON。",
                temperature=0.5,
                json_mode=True,
            )
        except HTTPException as exc:
            if exc.status_code != 502:
                raise
            raw = chat_completion(
                system_prompt,
                "请根据当前局势做出你的下一步决策，严格输出 JSON。",
                temperature=0.5,
                json_mode=False,
            )

        decision = _parse_llm_json(raw)
        thought = str(decision.get("thought", "")).strip()
        action = str(decision.get("action", "")).strip()
        amount = int(decision.get("amount") or 0)
        target_raw = str(decision.get("target", "")).strip()

        if action not in VALID_ACTIONS:
            raise HTTPException(status_code=502, detail=f"非法 action: {action}")

        self._apply_action(player_id, action, amount, thought, target_raw)
        self.game_state["actions_this_round"] += 1
        self._advance_turn()

        alive = self._alive_players()
        if len(alive) == 1:
            self._settle_round(alive[0])

        return self._turn_response(
            player_id,
            thought=thought,
            action=action,
            amount=amount,
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
        target: str = "",
    ) -> dict[str, Any]:
        info = self.game_state["players"][player_id]
        return {
            "player_id": player_id,
            "display_name": self.display_name(player_id),
            "skipped": skipped,
            "reason": reason,
            "thought": thought,
            "action": action,
            "amount": amount,
            "target": target,
            "pot": self.game_state["pot"],
            "balance": info["balance"],
            "phase": self.game_state["phase"],
            "current_player_id": self.current_player_id(),
        }

    def _apply_action(
        self,
        player_id: str,
        action: str,
        amount: int,
        thought: str,
        target_raw: str,
    ) -> None:
        info = self.game_state["players"][player_id]
        line = ""

        if action == "看牌":
            info["has_looked"] = True
            line = f"{self.display_name(player_id)} 选择 [看牌]，手牌: {format_cards(info['cards'])}"
        elif action == "弃牌":
            info["alive"] = False
            line = f"{self.display_name(player_id)} 选择 [弃牌]"
        elif action == "跟注":
            bet = self.game_state["current_bet"]
            cost = _actual_bet(bet, info["has_looked"])
            if cost > info["balance"]:
                raise HTTPException(status_code=400, detail=f"{player_id} 余额不足")
            info["balance"] -= cost
            self.game_state["pot"] += cost
            tag = "明注" if info["has_looked"] else "暗注"
            self._record_pot(player_id, cost, f"跟注/{tag}")
            line = f"{self.display_name(player_id)} 选择 [跟注/{tag}], 筹码变动: {cost}元"
        elif action == "加注":
            if amount <= self.game_state["current_bet"]:
                amount = self.game_state["current_bet"] + 10
            if amount > MAX_RAISE:
                amount = MAX_RAISE
            cost = _actual_bet(amount, info["has_looked"])
            if cost > info["balance"]:
                raise HTTPException(status_code=400, detail=f"{player_id} 余额不足")
            info["balance"] -= cost
            self.game_state["pot"] += cost
            self.game_state["current_bet"] = amount
            tag = "明注" if info["has_looked"] else "暗注"
            self._record_pot(player_id, cost, f"加注/{tag}")
            line = f"{self.display_name(player_id)} 选择 [加注/{tag}], 加注线: {amount}元, 筹码变动: {cost}元"
        elif action == "比牌":
            if not info["has_looked"]:
                raise HTTPException(status_code=400, detail="比牌前必须先看牌")
            target_id = _resolve_player_id(target_raw)
            if not target_id or target_id == player_id:
                alive_others = [p for p in self._alive_players() if p != player_id]
                if not alive_others:
                    raise HTTPException(status_code=400, detail="无可比牌对象")
                target_id = alive_others[0]
            self._do_compare(player_id, target_id)

        if thought:
            self.game_state["thoughts"].append(f"{self.display_name(player_id)}: {thought}")
        if line:
            self.game_state["action_logs"].append(line)

    def _do_compare(self, challenger_id: str, target_id: str) -> None:
        challenger = self.game_state["players"][challenger_id]
        target = self.game_state["players"][target_id]
        if not target["alive"]:
            raise HTTPException(status_code=400, detail="比牌目标已弃牌")
        compare_fee = _actual_bet(self.game_state["current_bet"], challenger["has_looked"])
        if compare_fee > challenger["balance"]:
            raise HTTPException(status_code=400, detail=f"{challenger_id} 余额不足以比牌")
        challenger["balance"] -= compare_fee
        self.game_state["pot"] += compare_fee
        self._record_pot(challenger_id, compare_fee, "比牌")

        cmp = compare_two_players(challenger["cards"], target["cards"])
        if cmp > 0:
            loser_id = target_id
            winner_id = challenger_id
        elif cmp < 0:
            loser_id = challenger_id
            winner_id = target_id
        else:
            loser_id = challenger_id
            winner_id = target_id

        self.game_state["players"][loser_id]["alive"] = False
        c_label = hand_label(challenger["cards"])
        t_label = hand_label(target["cards"])
        self.game_state["action_logs"].append(
            f"{self.display_name(challenger_id)} 与 {self.display_name(target_id)} [比牌]: "
            f"{format_cards(challenger['cards'])}({c_label}) vs "
            f"{format_cards(target['cards'])}({t_label}) → "
            f"{self.display_name(winner_id)} 胜，{self.display_name(loser_id)} 出局"
        )

    def _build_settlement(self, winner_id: str, pot: int) -> dict[str, Any]:
        winner_contribution = self._player_pot_contribution(winner_id)
        winner_net_win = max(pot - winner_contribution, 0)
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
            "pot_total": pot,
            "winner_net_win": winner_net_win,
            "players": details,
        }

    def _settle_round(self, winner_id: str) -> None:
        winner = self.game_state["players"][winner_id]
        pot = self.game_state["pot"]
        if pot > 0:
            winner["balance"] += pot
        self.game_state["pot"] = 0
        self.game_state["last_winner"] = winner_id
        settlement = self._build_settlement(winner_id, pot)
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
        ).strip()

    def public_status(self) -> dict[str, Any]:
        players: dict[str, Any] = {}
        for pid, info in self.game_state["players"].items():
            cards = info["cards"]
            players[pid] = {
                "display_name": self.display_name(pid),
                "balance": info["balance"],
                "has_looked": info["has_looked"],
                "alive": info["alive"],
                "cards": cards,
                "cards_display": format_cards(cards) if cards else "",
                "hand_label": hand_label(cards) if cards else "",
                "session_pnl": info["balance"] - INITIAL_BALANCE,
            }
        return {
            "round": self.game_state["round"],
            "max_rounds": self.game_state["max_rounds"],
            "pot": self.game_state["pot"],
            "current_bet": self.game_state["current_bet"],
            "phase": self.game_state["phase"],
            "game_enabled": self.game_enabled,
            "last_winner": self.game_state["last_winner"],
            "last_winner_name": (
                self.display_name(self.game_state["last_winner"])
                if self.game_state["last_winner"]
                else None
            ),
            "current_player_id": self.current_player_id(),
            "last_settlement": self.game_state["last_settlement"],
            "pot_ledger": list(self.game_state["pot_ledger"]),
            "players": players,
        }

    async def run_player_turn_async(self, player_id: str | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(self.run_player_turn, player_id)

    async def run_referee_commentary_async(self) -> str:
        return await asyncio.to_thread(self.run_referee_commentary)


_engine: ZhaJinhuaGameEngine | None = None


def get_engine() -> ZhaJinhuaGameEngine:
    global _engine
    if _engine is None:
        _engine = ZhaJinhuaGameEngine()
    return _engine
