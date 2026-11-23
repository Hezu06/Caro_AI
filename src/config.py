"""Shared rules and defaults. Coordinates are zero-based (row, column)."""

EMPTY = 0
X = 1
O = -1
BOARD_SIZE = 9
WIN_LENGTH = 5
DEFAULT_DEPTH = 2
DEFAULT_MAX_CANDIDATES = 12
DEFAULT_CANDIDATE_RADIUS = 2


def opponent(player: int) -> int:
    if type(player) is not int or player not in (X, O):
        raise ValueError("player must be X (1) or O (-1)")
    return -player
