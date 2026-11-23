"""Common agent interface and serializable per-decision statistics."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from src.core.board import BoardState, Move


@dataclass
class SearchStats:
    algorithm: str
    selected_move: Move | None = None
    depth: int = 0
    depth_reached: int = 0
    elapsed_seconds: float = 0.0
    nodes_visited: int = 0
    leaf_nodes: int = 0
    cutoffs: int = 0
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseAgent(ABC):
    """get_move never changes the caller's board; terminal positions return None.

    A nonterminal call returns a legal (row, col). The explicit player argument
    is the side to move, and all search scores use that root player's view.
    Instances hold last_stats and should not be shared by concurrent searches.
    """

    def __init__(self) -> None:
        self.last_stats = SearchStats(type(self).__name__)

    @abstractmethod
    def get_move(self, board: BoardState, player: int) -> Move | None:
        raise NotImplementedError
