# Integration contracts

## File map

| File | Responsibility |
|---|---|
| `src/config.py` | Rule constants and validated `opponent(player)` |
| `src/core/board.py` | `BoardState` protocol, `Move` type, concrete board rules |
| `src/core/game_engine.py` | Turns, history and applying agent moves |
| `src/agents/base_agent.py` | Abstract `BaseAgent` and `SearchStats` |
| `src/agents/candidate_moves.py` | Shared candidate filtering and ordering |
| `src/agents/minimax_agent.py` | Plain depth-limited MiniMax |
| `src/agents/alpha_beta_agent.py` | Depth-limited MiniMax with Alpha-Beta |
| `src/evaluation/evaluator.py` | Shared root-perspective evaluation |
| `src/agents/random_agent.py` | Seeded random baseline |
| `src/agents/human_agent.py` | Callback adapter for human input |
| `src/ui/cli.py` | Console input, rendering and configuration |
| `experiments/compare_search.py` | Same-position MiniMax/Alpha-Beta comparison |

## BoardState protocol

| Member | Contract |
|---|---|
| `size: int` | Board width and height |
| `win_length: int` | Minimum contiguous length needed to win |
| `get_cell(row, col) -> int` | Returns 0, 1 or -1; out-of-range access raises |
| `legal_moves() -> list[Move]` | All legal empty cells; empty list at terminal positions |
| `clone() -> BoardState` | Independent copy; modifying it must not change the source |
| `place(move, player) -> None` | Mutates only this board; rejects illegal moves and finished games |
| `winner() -> int or None` | Winning side, otherwise None |
| `is_full() -> bool` | True when no cells are empty |

The concrete `Board` additionally supplies `grid` (read-only snapshot),
`is_legal(move)` and `is_terminal()`. `Move` is `tuple[int, int]`.
A custom board can satisfy the protocol without inheriting `Board`.
Only standard two-player placements and the same winning rule are supported.

## BaseAgent

Subclass `BaseAgent`, call `super().__init__()`, and implement:

```python
def get_move(self, board: BoardState, player: int) -> Move | None:
    ...
```

Return a legal move for a nonterminal state. Return None only for a terminal
state. Do not modify the caller's board. Use `board.clone()` before simulation.
Replace `self.last_stats` at each decision with a `SearchStats` instance.
For MCTS, extend the statistics dataclass with iteration/rollout counts if needed;
keep the existing common fields available for the UI and experiment scripts.
MCTS can use `board.legal_moves()` for expansion and rollout; it does not need to
use MiniMax's candidate policy.

## GameEngine

```python
engine = GameEngine(board=None, current_player=1)
record = engine.play((4, 4))
# Or: record = engine.step(agent)
```

`play` validates and applies a move, records a frozen `MoveRecord(player, move)`,
then advances `current_player`, including after the final move. Read `winner`
and `is_over` to determine the result; do not infer the winner from current_player.
`step` returns None when already terminal; otherwise it asks the agent for a move
using a defensive board copy, then calls `play`. Invalid results raise ValueError.
History contains only moves played through this engine after initialization.
The current constructor accepts a concrete `Board`.

## UI adapters

```python
human = HumanAgent(move_provider)
# move_provider(board_snapshot, player) returns a legal (row, col).
```

The callback receives its own copy. This supports CLI input or a synchronous
adapter. A future event-driven GUI should store the clicked move and call
`engine.play(move)` from its event handler. Run AI searches on a worker with a
board snapshot and apply their result on the UI thread only if the game has not
changed. No GUI is included in this package.

Agent objects hold per-call mutable statistics and are not thread-safe. Use a
separate instance per concurrent search. Board input is copied by the agents'
search routines and by engine.step; the engine's board must not be modified by
another thread while a snapshot is being created.
