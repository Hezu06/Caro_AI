"""Rules only: five or more wins, including lines blocked at both ends."""
from __future__ import annotations

from typing import Protocol, Sequence, TypeAlias

from src.config import BOARD_SIZE, EMPTY, WIN_LENGTH, opponent

Move: TypeAlias = tuple[int, int]
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


class BoardState(Protocol):
    """Contract accepted by every agent and evaluator; no UI dependencies."""

    size: int
    win_length: int

    def get_cell(self, row: int, col: int) -> int: ...
    def legal_moves(self) -> list[Move]: ...
    def clone(self) -> BoardState: ...
    def place(self, move: Move, player: int) -> None: ...
    def winner(self) -> int | None: ...
    def is_full(self) -> bool: ...


class Board:
    def __init__(self, size: int = BOARD_SIZE, win_length: int = WIN_LENGTH,
                 grid: Sequence[Sequence[int]] | None = None):
        if type(size) is not int or type(win_length) is not int or not 2 <= win_length <= size:
            raise ValueError("Require integer size >= win_length >= 2")
        self.size = size
        self.win_length = win_length
        self._grid = [[EMPTY] * size for _ in range(size)]
        if grid is not None:
            if len(grid) != size or any(len(row) != size for row in grid):
                raise ValueError("grid must match size x size")
            if any(type(v) is not int or v not in (-1, 0, 1) for row in grid for v in row):
                raise ValueError("Cells must be EMPTY (0), X (1), or O (-1)")
            self._grid = [list(row) for row in grid]
        if len(self._winners()) > 1:
            raise ValueError("Both players cannot win in a valid position")

    @property
    def grid(self) -> tuple[tuple[int, ...], ...]:
        """Read-only snapshot: callers cannot mutate the board accidentally."""
        return tuple(tuple(row) for row in self._grid)

    def get_cell(self, row: int, col: int) -> int:
        if not (0 <= row < self.size and 0 <= col < self.size):
            raise IndexError("Cell outside board")
        return self._grid[row][col]

    def is_legal(self, move: Move) -> bool:
        r, c = move
        return (type(r) is int and type(c) is int and
                0 <= r < self.size and 0 <= c < self.size and self._grid[r][c] == EMPTY)

    def legal_moves(self) -> list[Move]:
        """Empty cells in row-major order; terminal boards have no legal moves."""
        if self.winner() is not None:
            return []
        return [(r, c) for r in range(self.size) for c in range(self.size)
                if self._grid[r][c] == EMPTY]

    def place(self, move: Move, player: int) -> None:
        opponent(player)  # Validate the player before modifying anything.
        if self.winner() is not None or not self.is_legal(move):
            raise ValueError("Illegal move or game already finished")
        r, c = move
        self._grid[r][c] = player

    def clone(self) -> Board:
        return Board(self.size, self.win_length, self._grid)

    def _winners(self) -> set[int]:
        winners: set[int] = set()
        for r in range(self.size):
            for c in range(self.size):
                player = self._grid[r][c]
                if player == EMPTY:
                    continue
                for dr, dc in DIRECTIONS:
                    # Count each maximal run once, from its first stone.
                    pr, pc = r - dr, c - dc
                    if 0 <= pr < self.size and 0 <= pc < self.size and self._grid[pr][pc] == player:
                        continue
                    length, nr, nc = 0, r, c
                    while 0 <= nr < self.size and 0 <= nc < self.size and self._grid[nr][nc] == player:
                        length += 1
                        nr, nc = nr + dr, nc + dc
                    if length >= self.win_length:
                        winners.add(player)
        return winners

    def winner(self) -> int | None:
        return next(iter(self._winners()), None)

    def is_full(self) -> bool:
        return all(cell != EMPTY for row in self._grid for cell in row)

    def is_terminal(self) -> bool:
        return self.winner() is not None or self.is_full()
