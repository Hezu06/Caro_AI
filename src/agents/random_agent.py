"""Seeded random baseline; uses all legal moves, without candidate filtering."""
import random
from time import perf_counter

from src.config import opponent
from src.core.board import BoardState, Move
from .base_agent import BaseAgent, SearchStats


class RandomAgent(BaseAgent):
    def __init__(self, seed: int | None = None):
        super().__init__()
        self.rng = random.Random(seed)

    def get_move(self, board: BoardState, player: int) -> Move | None:
        opponent(player)
        started = perf_counter()
        moves = board.legal_moves()
        move = self.rng.choice(moves) if moves else None
        self.last_stats = SearchStats(type(self).__name__, selected_move=move,
                                      elapsed_seconds=perf_counter() - started)
        return move
