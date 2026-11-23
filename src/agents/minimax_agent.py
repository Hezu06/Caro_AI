"""Depth-limited plain MiniMax: this implementation performs no pruning."""
from __future__ import annotations

import logging
from math import inf
from time import perf_counter
from typing import Callable

from src.config import (DEFAULT_CANDIDATE_RADIUS, DEFAULT_DEPTH,
                        DEFAULT_MAX_CANDIDATES, opponent)
from src.core.board import BoardState, Move
from src.evaluation.evaluator import evaluate
from .base_agent import BaseAgent, SearchStats
from .candidate_moves import candidate_moves

Evaluator = Callable[[BoardState, int], float]


class MinimaxAgent(BaseAgent):
    def __init__(self, depth: int = DEFAULT_DEPTH,
                 max_candidates: int | None = DEFAULT_MAX_CANDIDATES,
                 candidate_radius: int | None = DEFAULT_CANDIDATE_RADIUS,
                 evaluator: Evaluator = evaluate,
                 logger: logging.Logger | None = None):
        super().__init__()
        if type(depth) is not int or depth < 1:
            raise ValueError("depth must be a positive integer (including 2)")
        for name, value in (("max_candidates", max_candidates), ("candidate_radius", candidate_radius)):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError(f"{name} must be a positive integer or None")
        self.depth = depth
        self.max_candidates = max_candidates
        self.candidate_radius = candidate_radius
        self.evaluator = evaluator
        self.logger = logger or logging.getLogger(__name__)

    def _moves(self, board: BoardState, player: int) -> list[Move]:
        return candidate_moves(board, player, self.max_candidates, self.candidate_radius)

    def _visit(self, ply: int) -> None:
        self.last_stats.nodes_visited += 1
        self.last_stats.depth_reached = max(self.last_stats.depth_reached, ply)

    def _leaf(self, board: BoardState, remaining: int, root: int) -> float | None:
        # Terminal utility precedes the depth cutoff. The supplied evaluator
        # must preserve terminal win/loss/draw utilities (the default does).
        if board.winner() is not None or board.is_full() or remaining == 0:
            self.last_stats.leaf_nodes += 1
            return self.evaluator(board, root)
        return None

    def get_move(self, board: BoardState, player: int) -> Move | None:
        opponent(player)
        self.last_stats = SearchStats(type(self).__name__, depth=self.depth)
        started = perf_counter()
        try:
            move, score = self._choose(board, player)
            self.last_stats.selected_move = move
            self.last_stats.score = score
            return move
        finally:
            self.last_stats.elapsed_seconds = perf_counter() - started
            self.logger.info("decision %s", self.last_stats.to_dict())

    def _choose(self, board: BoardState, player: int) -> tuple[Move | None, float]:
        self._visit(0)  # Root is included in both algorithms' node counts.
        value = self._leaf(board, self.depth, player)
        if value is not None:
            return None, value
        best_move, best_value = None, -inf
        for move in self._moves(board, player):
            child = board.clone()
            child.place(move, player)
            value = self._search(child, self.depth - 1, opponent(player), player, 1)
            # Strict improvement keeps the first move when scores tie.
            if value > best_value:
                best_move, best_value = move, value
        return best_move, best_value

    def _search(self, board: BoardState, remaining: int,
                to_move: int, root: int, ply: int) -> float:
        self._visit(ply)
        leaf = self._leaf(board, remaining, root)
        if leaf is not None:
            return leaf
        maximizing = to_move == root
        value = -inf if maximizing else inf
        # MAX increases the root player's score; MIN reduces that same score.
        for move in self._moves(board, to_move):
            child = board.clone()
            child.place(move, to_move)
            score = self._search(child, remaining - 1, opponent(to_move), root, ply + 1)
            value = max(value, score) if maximizing else min(value, score)
        return value
