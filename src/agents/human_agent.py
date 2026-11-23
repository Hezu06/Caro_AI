"""UI-independent adapter: a GUI or CLI supplies a move callback."""
from typing import Callable

from src.config import opponent
from src.core.board import BoardState, Move
from .base_agent import BaseAgent, SearchStats


class HumanAgent(BaseAgent):
    def __init__(self, move_provider: Callable[[BoardState, int], Move]):
        super().__init__()
        self.move_provider = move_provider

    def get_move(self, board: BoardState, player: int) -> Move | None:
        opponent(player)
        legal = board.legal_moves()
        if not legal:
            self.last_stats = SearchStats(type(self).__name__)
            return None
        move = self.move_provider(board.clone(), player)
        if move not in legal:
            raise ValueError("Human move is not legal")
        self.last_stats = SearchStats(type(self).__name__, selected_move=move)
        return move
