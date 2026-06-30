"""炸金花确定性规则：洗牌、发牌、牌型、比大小。"""

from __future__ import annotations

import random
from typing import Literal

SUITS = ("H", "D", "C", "S")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")

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
    """返回 (类别序,  tiebreaker, 类别名)。"""
    if len(cards) != 3:
        raise ValueError("炸金花需 3 张牌")

    suits = [_card_parts(c)[0] for c in cards]
    values = sorted((_card_parts(c)[1] for c in cards), reverse=True)
    is_flush = len(set(suits)) == 1
    is_straight, straight_high = _is_straight(values)

    if values[0] == values[1] == values[2]:
        return _CATEGORY_ORDER["leopard"], (values[0],), "leopard"
    if is_straight and is_flush:
        return _CATEGORY_ORDER["straight_flush"], (straight_high,), "straight_flush"
    if is_flush:
        return _CATEGORY_ORDER["flush"], tuple(values), "flush"
    if is_straight:
        return _CATEGORY_ORDER["straight"], (straight_high,), "straight"
    if values[0] == values[1] or values[1] == values[2]:
        pair = values[1] if values[0] == values[1] else values[2]
        kicker = values[0] if values[0] != pair else values[2] if values[2] != pair else values[1]
        return _CATEGORY_ORDER["pair"], (pair, kicker), "pair"
    return _CATEGORY_ORDER["high_card"], tuple(values), "high_card"


def compare_hands(cards_a: list[str], cards_b: list[str]) -> int:
    """1 表示 A 赢，-1 表示 B 赢，0 表示平局。"""
    score_a = evaluate_hand(cards_a)
    score_b = evaluate_hand(cards_b)
    if score_a[0] != score_b[0] or score_a[1] != score_b[1]:
        return 1 if score_a > score_b else -1 if score_a < score_b else 0
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
