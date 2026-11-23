"""Turn management, history and agent integration; independent of any UI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config import X, opponent
from .board import Board, Move

if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent


@dataclass(frozen=True)
class MoveRecord:
    player: int
    move: Move


class GameEngine:
    def __init__(self, board: Board | None = None, current_player: int = X):
        opponent(current_player)
        self.board = board.clone() if board is not None else Board()
        self.current_player = current_player
        self.history: list[MoveRecord] = []

    @property
    def is_over(self) -> bool:
        return self.board.is_terminal()

    @property
    def winner(self) -> int | None:
        return self.board.winner()

    def play(self, move: Move) -> MoveRecord:
        if self.is_over:
            raise ValueError("Game already finished")
        record = MoveRecord(self.current_player, move)
        self.board.place(move, self.current_player)
        self.history.append(record)
        self.current_player = opponent(self.current_player)
        return record

    def step(self, agent: BaseAgent) -> MoveRecord | None:
        if self.is_over:
            return None
        # Defensive copy also protects the engine from third-party agents.
        move = agent.get_move(self.board.clone(), self.current_player)
        if move is None:
            raise ValueError("Agent returned None for a nonterminal position")
        return self.play(move)
