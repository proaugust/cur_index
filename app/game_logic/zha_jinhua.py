"""炸金花确定性规则：洗牌、发牌、牌型、比大小。"""

from __future__ import annotations

import random
from typing import Literal

SUITS = ("H", "D", "C", "S")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")

# 花色决胜：黑桃 > 红桃 > 梅花 > 方块
SUIT_ORDER: dict[str, int] = {"S": 4, "H": 3, "C": 2, "D": 1}

HandCategory = Literal["leopard", "straight_flush", "flush", "straight", "pair", "high_card"]

_CATEGORY_ORDER: dict[HandCategory, int] = {
    "leopard": 6,
    "straight_flush": 5,
    "flush": 4,
    "straight": 3,
    "pair": 2,
    "high_card": 1,
}


def new_deck() -> list[str]:
    return [f"{suit}{rank}" for suit in SUITS for rank in RANKS]


def shuffle_and_deal(player_ids: list[str]) -> dict[str, list[str]]:
    deck = new_deck()
    random.shuffle(deck)
    return {pid: deck[i * 3 : (i + 1) * 3] for i, pid in enumerate(player_ids)}


def _rank_value(rank: str) -> int:
    if rank == "A":
        return 14
    if rank == "T":
        return 10
    if rank == "J":
        return 11
    if rank == "Q":
        return 12
    if rank == "K":
        return 13
    return int(rank)


def _card_parts(card: str) -> tuple[str, int]:
    return card[0], _rank_value(card[1:])


def _suit_strength(card: str) -> int:
    return SUIT_ORDER[card[0]]


def _max_suit_for_rank(cards: list[str], rank_val: int) -> int:
    suits = [_suit_strength(c) for c in cards if _card_parts(c)[1] == rank_val]
    return max(suits) if suits else 0


def _rank_suit_keys(cards: list[str]) -> tuple[tuple[int, int], ...]:
    """按点数降序、同点按花色降序排列，用于金花/单张决胜。"""
    keys = [(_card_parts(c)[1], _suit_strength(c)) for c in cards]
    return tuple(sorted(keys, reverse=True))


def _straight_high_value(values: list[int]) -> int:
    uniq = sorted(set(values))
    if set(uniq) == {14, 2, 3}:
        return 3
    return uniq[2] if len(uniq) == 3 else 0


def _is_straight(values: list[int]) -> tuple[bool, int]:
    """返回 (是否顺子, 顺子最大牌点)。支持 A-2-3。"""
    uniq = sorted(set(values))
    if len(uniq) != 3:
        return False, 0
    if uniq[2] - uniq[0] == 2 and len({uniq[1] - uniq[0], uniq[2] - uniq[1]}) == 1:
        return True, uniq[2]
    if set(uniq) == {14, 2, 3}:
        return True, 3
    return False, 0


def evaluate_hand(cards: list[str]) -> tuple[int, tuple[int, ...], HandCategory]:
    """返回 (类别序, tiebreaker, 类别名)。tiebreaker 含花色权重。"""
    if len(cards) != 3:
        raise ValueError("炸金花需 3 张牌")

    values = sorted((_card_parts(c)[1] for c in cards), reverse=True)
    is_flush = len({_card_parts(c)[0] for c in cards}) == 1
    is_straight, straight_high = _is_straight(values)

    if values[0] == values[1] == values[2]:
        rank = values[0]
        return _CATEGORY_ORDER["leopard"], (rank, _max_suit_for_rank(cards, rank)), "leopard"
    if is_straight and is_flush:
        return (
            _CATEGORY_ORDER["straight_flush"],
            (straight_high, _max_suit_for_rank(cards, straight_high)),
            "straight_flush",
        )
    if is_flush:
        flat: list[int] = []
        for rank, suit in _rank_suit_keys(cards):
            flat.extend((rank, suit))
        return _CATEGORY_ORDER["flush"], tuple(flat), "flush"
    if is_straight:
        return (
            _CATEGORY_ORDER["straight"],
            (straight_high, _max_suit_for_rank(cards, straight_high)),
            "straight",
        )
    if values[0] == values[1] or values[1] == values[2]:
        pair = values[1] if values[0] == values[1] else values[2]
        kicker = values[0] if values[0] != pair else values[2] if values[2] != pair else values[1]
        return (
            _CATEGORY_ORDER["pair"],
            (pair, _max_suit_for_rank(cards, pair), kicker, _max_suit_for_rank(cards, kicker)),
            "pair",
        )
    flat = []
    for rank, suit in _rank_suit_keys(cards):
        flat.extend((rank, suit))
    return _CATEGORY_ORDER["high_card"], tuple(flat), "high_card"


def compare_hands(cards_a: list[str], cards_b: list[str]) -> int:
    """1 表示 A 赢，-1 表示 B 赢，0 表示平局（同牌同点同花，极罕见）。"""
    score_a = evaluate_hand(cards_a)
    score_b = evaluate_hand(cards_b)
    if score_a > score_b:
        return 1
    if score_a < score_b:
        return -1
    return 0


def judge_winner(hands: dict[str, list[str]]) -> str:
    """多玩家比牌，返回胜者 player_id。"""
    if not hands:
        raise ValueError("无有效手牌")
    winner = next(iter(hands))
    for pid, cards in hands.items():
        if compare_hands(cards, hands[winner]) > 0:
            winner = pid
    return winner


def format_cards(cards: list[str]) -> str:
    suit_map = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
    return " ".join(f"{suit_map.get(c[0], c[0])}{c[1:]}" for c in cards)


_CATEGORY_LABELS: dict[HandCategory, str] = {
    "leopard": "豹子",
    "straight_flush": "顺金",
    "flush": "金花",
    "straight": "顺子",
    "pair": "对子",
    "high_card": "单张",
}


def hand_label(cards: list[str]) -> str:
    return _CATEGORY_LABELS[evaluate_hand(cards)[2]]


def compare_two_players(cards_a: list[str], cards_b: list[str]) -> int:
    """1 表示 A 赢，-1 表示 B 赢，0 表示平局。"""
    return compare_hands(cards_a, cards_b)


def stake_at_line_for(
    bet_line: int,
    *,
    actor_has_looked: bool,
    has_prev_actor: bool = False,
    compare_target_blind: bool = False,
) -> int:
    """按发话规则计算玩家在 bet_line（当前暗注标准）注线下的应付总额（非增量）。

    暗注（蒙牌）：恒 = bet_line。
    明注（看牌）且本局第一个发话（无上一发话者、且非比蒙牌）：= bet_line。
    其余明注（有上一发话者，或比牌对象为蒙牌）：= bet_line×2。
    """
    if not actor_has_looked:
        return bet_line
    if not has_prev_actor and not compare_target_blind:
        return bet_line
    return bet_line * 2
