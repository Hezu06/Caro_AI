"""Shared deterministic heuristic, always measured from MAX's perspective."""
from src.config import EMPTY, opponent
from src.core.board import BoardState, DIRECTIONS

WIN_SCORE = 1_000_000.0


def evaluate(board: BoardState, player: int) -> float:
    """Terminal utility dominates every heuristic score.

    Score unblocked win-length windows (also detects gapped threats), add
    bonuses for contiguous open-ended runs, and a small centrality bonus.
    This is an estimate, not a guarantee of winning beyond the search horizon.
    """
    other = opponent(player)
    winner = board.winner()
    if winner is not None:
        return WIN_SCORE if winner == player else -WIN_SCORE
    if board.is_full():
        return 0.0

    def strength(side: int) -> float:
        total = 0.0
        n, k = board.size, board.win_length
        for r in range(n):
            for c in range(n):
                for dr, dc in DIRECTIONS:
                    er, ec = r + (k - 1) * dr, c + (k - 1) * dc
                    if 0 <= er < n and 0 <= ec < n:
                        cells = [board.get_cell(r + i * dr, c + i * dc) for i in range(k)]
                        if -side not in cells:
                            count = cells.count(side)
                            if count:
                                total += 10 ** (count - 1)
                if board.get_cell(r, c) != side:
                    continue
                mid = (n - 1) / 2
                total += 0.1 * (n - abs(r - mid) - abs(c - mid))
                for dr, dc in DIRECTIONS:
                    pr, pc = r - dr, c - dc
                    if 0 <= pr < n and 0 <= pc < n and board.get_cell(pr, pc) == side:
                        continue
                    length, nr, nc = 0, r, c
                    while 0 <= nr < n and 0 <= nc < n and board.get_cell(nr, nc) == side:
                        length += 1
                        nr, nc = nr + dr, nc + dc
                    open_ends = int(0 <= pr < n and 0 <= pc < n and board.get_cell(pr, pc) == EMPTY)
                    open_ends += int(0 <= nr < n and 0 <= nc < n and board.get_cell(nr, nc) == EMPTY)
                    if length >= 2 and open_ends:
                        total += open_ends * 10 ** (length - 1)
        return total

    score = strength(player) - strength(other)
    return max(-WIN_SCORE / 2, min(WIN_SCORE / 2, score))
