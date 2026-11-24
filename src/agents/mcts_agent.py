"""Monte Carlo Tree Search with UCT and random rollouts."""

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
    untried_moves: list[Move]
    children: dict[Move, _Node] = field(default_factory=dict)
    visits: int = 0
    value_sum: float = 0.0  # Accumulated reward from the root player's view.


class MCTSAgent(BaseAgent):
    def __init__(
        self,
        iterations: int = 1000,
        exploration: float = sqrt(2.0),
        seed: int | None = None,
    ) -> None:
        super().__init__()
        if type(iterations) is not int or iterations < 1:
            raise ValueError("iterations must be a positive integer")
        if not isfinite(exploration) or exploration < 0:
            raise ValueError("exploration must be finite and non-negative")

        self.iterations = iterations
        self.exploration = exploration
        self.rng = Random(seed)

    def get_move(self, board: BoardState, player: int) -> Move | None:
        opponent(player)  # Validate the side to move.
        started = perf_counter()
        stats = SearchStats(type(self).__name__)
        self.last_stats = stats

        legal_moves = board.legal_moves()
        if not legal_moves:
            stats.elapsed_seconds = perf_counter() - started
            return None

        if len(legal_moves) == 1:
            stats.selected_move = legal_moves[0]
            stats.elapsed_seconds = perf_counter() - started
            return stats.selected_move

        root = _Node(legal_moves.copy())
        stats.nodes_visited = 1

        for _ in range(self.iterations):
            simulation = board.clone()
            node = root
            path = [root]
            current_player = player

            # Selection: descend with UCT once all moves at this node are expanded.
            while not node.untried_moves and node.children:
                move, node = self._select_child(node, current_player == player)
                simulation.place(move, current_player)
                current_player = opponent(current_player)
                path.append(node)

            # Expansion: sample one previously untried move.
            if node.untried_moves:
                index = self.rng.randrange(len(node.untried_moves))
                move = node.untried_moves.pop(index)
                simulation.place(move, current_player)
                current_player = opponent(current_player)
                child = _Node(simulation.legal_moves())
                node.children[move] = child
                node = child
                path.append(node)

            # Simulation: play uniformly random moves until the game ends.
            winner = self._rollout(simulation, current_player, node.untried_moves)
            reward = 0.5 if winner is None else float(winner == player)

            # Backpropagation: update the path from the root player's perspective.
            for visited in path:
                visited.visits += 1
                visited.value_sum += reward

            depth = len(path) - 1
            stats.nodes_visited += depth
            stats.leaf_nodes += 1
            stats.depth_reached = max(stats.depth_reached, depth)

        # Choose the most visited move, using average reward to break ties.
        move, best = max(
            root.children.items(),
            key=lambda item: (item[1].visits, item[1].value_sum / item[1].visits),
        )
        stats.selected_move = move
        stats.score = best.value_sum / best.visits
        stats.elapsed_seconds = perf_counter() - started
        return move

    def _select_child(self, node: _Node, root_turn: bool) -> tuple[Move, _Node]:
        log_parent_visits = log(node.visits)

        def uct(item: tuple[Move, _Node]) -> float:
            child = item[1]
            mean = child.value_sum / child.visits
            exploitation = mean if root_turn else 1.0 - mean
            exploration_bonus = self.exploration * sqrt(
                log_parent_visits / child.visits
            )
            return exploitation + exploration_bonus

        # Each child receives its first visit in the iteration that creates it.
        return max(node.children.items(), key=uct)

    def _rollout(self, board: BoardState, player: int, legal_moves: list[Move]) -> int | None:
        if not legal_moves:
            return board.winner()

        remaining = legal_moves.copy()
        self.rng.shuffle(remaining)
        for move in remaining:
            board.place(move, player)
            winner = board.winner()
            if winner is not None:
                return winner
            player = opponent(player)

        return None