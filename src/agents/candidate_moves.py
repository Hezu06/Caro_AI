"""Identical move selection and ordering for both search algorithms."""
from src.config import DEFAULT_CANDIDATE_RADIUS, DEFAULT_MAX_CANDIDATES, opponent
from src.core.board import BoardState, DIRECTIONS, Move


def _would_win(board: BoardState, move: Move, player: int) -> bool:
    r, c = move
    for dr, dc in DIRECTIONS:
        count = 1
        for sign in (-1, 1):
            nr, nc = r + sign * dr, c + sign * dc
            while (0 <= nr < board.size and 0 <= nc < board.size and
                   board.get_cell(nr, nc) == player):
                count += 1
                nr, nc = nr + sign * dr, nc + sign * dc
        if count >= board.win_length:
            return True
    return False


def candidate_moves(board: BoardState, player: int,
                    max_candidates: int | None = DEFAULT_MAX_CANDIDATES,
                    radius: int | None = DEFAULT_CANDIDATE_RADIUS) -> list[Move]:
    """Filter by Chebyshev distance, rank tactically, then keep at most K.

    Own immediate wins come first, followed by opponent winning squares
    (potential blocks), nearby stones, centrality, then row/column. All ordering
    is deterministic. None disables the corresponding filter. Even with a
    radius filter, immediate winning/blocking squares are always considered
    before the cap. A hard cap can still discard relevant moves.
    """
    other = opponent(player)
    for name, value in (("max_candidates", max_candidates), ("radius", radius)):
        if value is not None and (type(value) is not int or value < 1):
            raise ValueError(f"{name} must be a positive integer or None")
    legal = board.legal_moves()
    occupied = [(r, c) for r in range(board.size) for c in range(board.size)
                if board.get_cell(r, c) != 0]
    mid = (board.size - 1) / 2
    ranked = []
    for move in legal:
        r, c = move
        win = _would_win(board, move, player)
        block = _would_win(board, move, other)
        near = radius is None or not occupied or any(
            max(abs(r - rr), abs(c - cc)) <= radius for rr, cc in occupied)
        if not (near or win or block):
            continue
        neighbors = sum(max(abs(r - rr), abs(c - cc)) <= 1 for rr, cc in occupied)
        key = (-int(win), -int(block), -neighbors, abs(r - mid) + abs(c - mid), r, c)
        ranked.append((key, move))
    ranked.sort()
    moves = [move for _, move in ranked]
    return moves if max_candidates is None else moves[:max_candidates]
