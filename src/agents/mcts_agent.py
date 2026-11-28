"""Basic MCTS with UCT and uniform random rollouts to terminal states."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, log, sqrt
from random import Random
from time import perf_counter

from src.config import opponent
from src.core.board import BoardState, Move

from .base_agent import BaseAgent, SearchStats


@dataclass
class _Node:
    untried: list[Move]
    children: dict[Move, _Node] = field(default_factory=dict)
    visits: int = 0
    reward_sum: float = 0.0  # From the side to move at this node.

    @property
    def parent_mean(self) -> float:
        return -self.reward_sum / self.visits


class MCTSAgent(BaseAgent):
    def __init__(
        self,
        iterations: int = 1000,
        exploration: float = sqrt(2.0),
        seed: int | None = None,
        *,
        root_policy: str = "visits",
    ) -> None:
        super().__init__()
        if type(iterations) is not int or iterations < 1:
            raise ValueError("iterations must be a positive integer")
        if not isfinite(exploration) or exploration <= 0:
            raise ValueError("exploration must be finite and positive")
        if root_policy not in ("visits", "mean"):
            raise ValueError("root_policy must be 'visits' or 'mean'")
        self.iterations = iterations
        self.exploration = exploration
        self.root_policy = root_policy
        self.rng = Random(seed)

    def get_move(self, board: BoardState, player: int) -> Move | None:
        opponent(player)
        started = perf_counter()
        self.last_stats = stats = SearchStats(type(self).__name__)
        try:
            root = _Node(list(board.legal_moves()))
            if not root.untried:
                return None

            stats.nodes_visited = 1
            for _ in range(self.iterations):
                simulation = board.clone()
                to_move = player
                node = root
                path = [root]

                # Selection: follow UCT through fully expanded nodes.
                while not node.untried and node.children:
                    move, node = self._select_child(node)
                    simulation.place(move, to_move)
                    to_move = opponent(to_move)
                    path.append(node)

                # Expansion: consider every legal move in a random order.
                if node.untried:
                    move = node.untried.pop(self.rng.randrange(len(node.untried)))
                    simulation.place(move, to_move)
                    to_move = opponent(to_move)
                    child = _Node(list(simulation.legal_moves()))
                    node.children[move] = child
                    node = child
                    path.append(node)

                reward = self._rollout(simulation, to_move, node.untried)
                for visited in reversed(path):
                    visited.visits += 1
                    visited.reward_sum += reward
                    reward = -reward

                depth = len(path) - 1
                stats.nodes_visited += depth
                stats.leaf_nodes += 1
                stats.depth_reached = max(stats.depth_reached, depth)

            def rank(item: tuple[Move, _Node]) -> tuple[float, float]:
                _, child = item
                if self.root_policy == "mean":
                    return child.parent_mean, child.visits
                return child.visits, child.parent_mean

            move, child = max(root.children.items(), key=rank)
            stats.selected_move = move
            stats.score = child.parent_mean
            return move
        finally:
            stats.elapsed_seconds = perf_counter() - started

    def _select_child(self, node: _Node) -> tuple[Move, _Node]:
        parent_log = log(node.visits)

        def uct(item: tuple[Move, _Node]) -> float:
            _, child = item
            return child.parent_mean + self.exploration * sqrt(parent_log / child.visits)

        return max(node.children.items(), key=uct)

    def _rollout(self, board: BoardState, player: int, legal_moves: list[Move]) -> float:
        # A shuffled list is equivalent to sampling uniform legal placements
        # one at a time. Stop as soon as the actual game rules give a winner.
        remaining = legal_moves.copy()
        self.rng.shuffle(remaining)
        to_move = player
        winner = board.winner() if not remaining else None
        for move in remaining:
            board.place(move, to_move)
            winner = board.winner()
            if winner is not None:
                break
            to_move = opponent(to_move)
        if winner is None:
            return 0.0
        return 1.0 if winner == player else -1.0
