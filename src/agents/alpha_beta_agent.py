"""MiniMax with Alpha-Beta; shares configuration, evaluation and statistics."""
from math import inf

from src.config import opponent
from src.core.board import BoardState, Move
from .minimax_agent import MinimaxAgent


class AlphaBetaAgent(MinimaxAgent):
    """Separate search recursion; inheritance only reuses common infrastructure."""

    def _choose(self, board: BoardState, player: int) -> tuple[Move | None, float]:
        self._visit(0)
        leaf = self._leaf(board, self.depth, player)
        if leaf is not None:
            return None, leaf
        best_move, best_value = None, -inf
        alpha, beta = -inf, inf
        for move in self._moves(board, player):
            child = board.clone()
            child.place(move, player)
            value = self._search_ab(child, self.depth - 1, opponent(player),
                                    player, 1, alpha, beta)
            if value > best_value:
                best_move, best_value = move, value
            alpha = max(alpha, best_value)
        return best_move, best_value

    def _search_ab(self, board: BoardState, remaining: int, to_move: int,
                   root: int, ply: int, alpha: float, beta: float) -> float:
        self._visit(ply)
        leaf = self._leaf(board, remaining, root)
        if leaf is not None:
            return leaf
        maximizing = to_move == root
        value = -inf if maximizing else inf
        moves = self._moves(board, to_move)
        for index, move in enumerate(moves):
            child = board.clone()
            child.place(move, to_move)
            score = self._search_ab(child, remaining - 1, opponent(to_move),
                                    root, ply + 1, alpha, beta)
            value = max(value, score) if maximizing else min(value, score)
            if maximizing:
                alpha = max(alpha, value)
            else:
                beta = min(beta, value)
            if alpha >= beta:
                # Count cutoff events only when at least one sibling is skipped.
                if index + 1 < len(moves):
                    self.last_stats.cutoffs += 1
                break
        return value
