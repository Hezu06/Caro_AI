"""UCT with tactical move filtering and short, guided rollouts."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from math import isfinite, log, sqrt, tanh
from random import Random
from time import perf_counter

from src.config import X, opponent
from src.core.board import BoardState, DIRECTIONS, Move

from .base_agent import BaseAgent, SearchStats


def _bits(mask: int) -> Iterator[int]:
    while mask:
        bit = mask & -mask
        yield bit
        mask ^= bit


@dataclass(frozen=True)
class _Geometry:
    windows: tuple[int, ...]
    center: tuple[float, ...]
    board_mask: int


@lru_cache(maxsize=16)
def _geometry(size: int, length: int) -> _Geometry:
    windows = []
    middle = (size - 1) / 2
    center = []
    for row in range(size):
        for col in range(size):
            center.append(1 / (1 + abs(row - middle) + abs(col - middle)))
            for dr, dc in DIRECTIONS:
                end_row = row + (length - 1) * dr
                end_col = col + (length - 1) * dc
                if 0 <= end_row < size and 0 <= end_col < size:
                    windows.append(sum(
                        1 << ((row + i * dr) * size + col + i * dc)
                        for i in range(length)
                    ))
    return _Geometry(tuple(windows), tuple(center), (1 << (size * size)) - 1)


@dataclass
class _Patterns:
    wins: int = 0
    followups: dict[int, int] = field(default_factory=dict)
    weights: dict[int, int] = field(default_factory=dict)
    strength: int = 0
    won: bool = False

    def add_window(self, empty: int, count: int) -> None:
        vacancies = empty.bit_count()
        if vacancies == 0:
            self.won = True
            return
        if vacancies == 1:
            self.wins |= empty
        if vacancies == 2:
            first = empty & -empty
            second = empty ^ first
            self.followups[first] = self.followups.get(first, 0) | second
            self.followups[second] = self.followups.get(second, 0) | first

        weight = 8 ** (count - 1)
        self.strength += weight
        for bit in _bits(empty):
            self.weights[bit] = self.weights.get(bit, 0) + weight


def _analyse(own_stones: int, other_stones: int, geometry: _Geometry) -> tuple[_Patterns, _Patterns]:
    own, other = _Patterns(), _Patterns()
    for window in geometry.windows:
        ours = window & own_stones
        theirs = window & other_stones
        if ours and not theirs:
            own.add_window(window ^ ours, ours.bit_count())
        elif theirs and not ours:
            other.add_window(window ^ theirs, theirs.bit_count())
    return own, other


def _forcing_win(
    stones: int, other_stones: int, geometry: _Geometry, depth: int,
    cache: dict[tuple[int, int, int], int],
) -> int:
    """Prove a win using only moves that force an immediate block."""
    key = stones, other_stones, depth
    if key in cache:
        return cache[key]

    own, other = _analyse(stones, other_stones, geometry)
    if own.won or other.won:
        cache[key] = 0
        return 0
    move = own.wins & -own.wins
    if not move and depth and other.wins.bit_count() < 2:
        for attack, replies in own.followups.items():
            if other.wins and attack != other.wins:
                continue
            if replies.bit_count() > 1 or _forcing_win(
                stones | attack, other_stones | replies, geometry, depth - 1, cache
            ):
                move = attack
                break
    cache[key] = move
    return move


@dataclass
class _Node:
    moves: list[int]
    estimate: float
    solved: float | None = None
    complete: bool = True
    children: dict[int, _Node] = field(default_factory=dict)
    visits: int = 0
    value_sum: float = 0.0


def _position(stones: int, other_stones: int, geometry: _Geometry, cap: int) -> _Node:
    """Score a position from the perspective of the side about to play."""
    own, other = _analyse(stones, other_stones, geometry)
    if own.won or other.won:
        return _Node([], 0.5, float(own.won))

    empty = geometry.board_mask ^ (stones | other_stones)
    if not empty:
        return _Node([], 0.5, 0.5)
    if own.wins:
        return _Node(list(_bits(own.wins)), 0.5, 1.0)
    if other.wins.bit_count() > 1:
        # A single move cannot cover two distinct winning squares.
        return _Node(list(_bits(other.wins)), 0.5, 0.0)

    estimate = 0.5 + 0.45 * tanh((own.strength - other.strength) / 150)
    if other.wins:
        return _Node([other.wins], estimate)

    forks = [move for move, replies in own.followups.items() if replies.bit_count() > 1]
    if forks:
        # The opponent cannot win immediately and can only cover one reply.
        return _Node(forks, 0.5, 1.0)

    opponent_forks = {
        move: replies for move, replies in other.followups.items()
        if replies.bit_count() > 1
    }

    def rank(move: int) -> tuple[int, float, float]:
        reply = own.followups.get(move, 0)
        # A single threat forces the reply. Otherwise any opposing fork is legal.
        forks_left = (
            sum((replies & ~move).bit_count() > 1 for fork, replies in opponent_forks.items()
                if fork != move and (not reply or fork == reply))
        )
        strength = own.weights.get(move, 0) * 1.1 + other.weights.get(move, 0)
        center = geometry.center[move.bit_length() - 1]
        return forks_left, -(strength + 45 * bool(reply) + 2 * center), -center

    ranked = sorted((rank(move), move) for move in _bits(empty))
    if ranked[0][0][0]:
        # Every move lets the opponent make an unanswerable pair of threats.
        return _Node([ranked[0][1]], 0.5, 0.0)
    safe = [move for (forks_left, _, _), move in ranked if forks_left == 0]
    return _Node(safe[:cap], estimate, complete=len(safe) <= cap)


class MCTSAgent(BaseAgent):
    def __init__(
        self,
        iterations: int = 1000,
        exploration: float = 0.65,
        seed: int | None = None,
        *,
        max_candidates: int = 10,
        rollout_depth: int = 4,
        root_policy: str = "visits",
    ) -> None:
        super().__init__()
        for name, value in (("iterations", iterations), ("max_candidates", max_candidates),
                            ("rollout_depth", rollout_depth)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not isfinite(exploration) or exploration < 0:
            raise ValueError("exploration must be finite and non-negative")
        if root_policy not in ("visits", "mean"):
            raise ValueError("root_policy must be 'visits' or 'mean'")
        self.iterations = iterations
        self.exploration = exploration
        self.max_candidates = max_candidates
        self.rollout_depth = rollout_depth
        self.root_policy = root_policy
        self.rng = Random(seed)

    def get_move(self, board: BoardState, player: int) -> Move | None:
        opponent(player)
        started = perf_counter()
        self.last_stats = stats = SearchStats(type(self).__name__)
        try:
            if board.winner() is not None or board.is_full():
                return None

            size = board.size
            geometry = _geometry(size, board.win_length)
            x = o = 0
            for row in range(size):
                for col in range(size):
                    stone = board.get_cell(row, col)
                    if stone == X:
                        x |= 1 << (row * size + col)
                    elif stone:
                        o |= 1 << (row * size + col)

            own, other = (x, o) if player == X else (o, x)
            if not own and not other:
                stats.selected_move = (size // 2, size // 2)
                return stats.selected_move

            root = _position(own, other, geometry, self.max_candidates)
            stats.nodes_visited = 1
            if root.solved is not None or len(root.moves) == 1:
                move = root.moves[0]
                stats.score = root.solved
            else:
                cache: dict[tuple[int, int, int], int] = {}
                move = _forcing_win(own, other, geometry, 5, cache)
                if move:
                    stats.score = 1.0
                else:
                    safe = [candidate for candidate in root.moves if not _forcing_win(
                        other, own | candidate, geometry, 4, cache
                    )]
                    if safe:
                        root.moves = safe
                    move, stats.score = self._search(root, own, other, geometry)
            stats.selected_move = divmod(move.bit_length() - 1, size)
            return stats.selected_move
        finally:
            stats.elapsed_seconds = perf_counter() - started

    def _search(self, root: _Node, own: int, other: int, geometry: _Geometry) -> tuple[int, float]:
        stats = self.last_stats
        for _ in range(self.iterations):
            current, waiting = own, other
            node = root
            path = [node]

            while node.solved is None:
                if len(node.children) < len(node.moves):
                    move = node.moves[len(node.children)]
                    current, waiting = waiting, current | move
                    child = _position(current, waiting, geometry, self.max_candidates)
                    node.children[move] = child
                    node = child
                    path.append(node)
                    break

                move, node = self._select_child(node)
                current, waiting = waiting, current | move
                path.append(node)

            reward = self._rollout(node, current, waiting, geometry)
            # Each node stores rewards from its own side-to-move perspective.
            for visited in reversed(path):
                visited.visits += 1
                visited.value_sum += reward
                reward = 1.0 - reward
                if visited.solved is None:
                    children = [child.solved for child in visited.children.values()]
                    if 0.0 in children:
                        visited.solved = 1.0
                    elif (visited.complete and len(children) == len(visited.moves)
                          and all(value is not None for value in children)):
                        visited.solved = 1.0 - min(value for value in children if value is not None)

            depth = len(path) - 1
            stats.nodes_visited += depth
            stats.leaf_nodes += 1
            stats.depth_reached = max(stats.depth_reached, depth)
            if root.solved is not None:
                best = next(move for move, child in root.children.items()
                            if child.solved == 1.0 - root.solved)
                return best, root.solved

        return self._choose_root_move(root)

    def _choose_root_move(self, root: _Node) -> tuple[int, float]:
        def rank_child(item: tuple[int, _Node]) -> tuple[bool, float, float]:
            _, child = item
            mean = 1.0 - child.value_sum / child.visits
            if self.root_policy == "mean":
                return child.solved != 1.0, mean, child.visits
            return child.solved != 1.0, child.visits, mean

        move, best = max(root.children.items(), key=rank_child)
        return move, 1.0 - best.value_sum / best.visits

    def _select_child(self, node: _Node) -> tuple[int, _Node]:
        log_visits = log(node.visits)

        def uct(item: tuple[int, _Node]) -> float:
            _, child = item
            mean = 1.0 - child.value_sum / child.visits
            return mean + self.exploration * sqrt(log_visits / child.visits)

        unexplored = [item for item in node.children.items() if item[1].solved is None]
        return max(unexplored or node.children.items(), key=uct)

    def _rollout(self, node: _Node, current: int, waiting: int, geometry: _Geometry) -> float:
        sign = 1
        for _ in range(self.rollout_depth):
            if node.solved is not None:
                break
            # The best few moves remain plausible while preserving rollout diversity.
            move = self.rng.choice(node.moves[:3])
            current, waiting = waiting, current | move
            node = _position(current, waiting, geometry, self.max_candidates)
            sign = -sign

        value = node.solved if node.solved is not None else node.estimate
        return value if sign == 1 else 1.0 - value
