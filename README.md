# Caro AI: MiniMax and Alpha-Beta

A runnable Python foundation based on the supplied directory diagram. This is a new
implementation, not a patch against an existing repository. Requires Python 3.10+;
no third-party packages are required.

Implemented: board rules, engine, agent interface/statistics, shared evaluator and
candidate policy, separate MiniMax and Alpha-Beta search, random/human adapters,
CLI, comparison script and tests. MCTS, heuristic MCTS, CustomTkinter GUI and
plotting are future modules; the interfaces below support adding them.

## Run

From the extracted `Caro_AI` folder:

```sh
python main.py
python main.py --x minimax --o alpha-beta --depth 2 --max-candidates 12 --radius 2
python main.py --x human --o alpha-beta --log decisions.log
python -m unittest discover -s tests -v
python -m experiments.compare_search --depth 2 --repeats 3
```

Human input uses `row column`, e.g. `4 4`. Coordinates are zero-based.
`X=1`, `O=-1`, `EMPTY=0`. Five or more stones in any of four directions wins,
even when blocked at both ends. A full board without a winner is a draw.

## Use the agents

```python
from src.core import GameEngine
from src.agents import MinimaxAgent, AlphaBetaAgent

game = GameEngine()
agents = {1: MinimaxAgent(depth=2), -1: AlphaBetaAgent(depth=2)}
while not game.is_over:
    agent = agents[game.current_player]
    record = game.step(agent)
    print(record, agent.last_stats.to_dict())
```

For one decision, call `agent.get_move(board, player)`; it returns `(row, col)`
or `None` for a terminal position, without altering the supplied board.
`player` explicitly identifies whose turn it is. `GameEngine` tracks turns;
`Board` deliberately does not infer them from stone counts, so controlled test
positions are possible. If initializing from a custom board, supply the correct
`current_player` to the engine. The board validates dimensions, cell values and
contradictory winners, but does not validate historical reachability.

## Search configuration

Both classes accept the same arguments:

```python
agent = AlphaBetaAgent(
    depth=2,
    max_candidates=12,
    candidate_radius=2,
)
```

- `depth`: maximum number of individual moves (plies), including the root move.
  At depth 2, search includes the AI move and one opponent reply.
- `max_candidates`: strict cap per expanded position. `None` disables it.
- `candidate_radius`: Chebyshev distance from existing stones. `None` disables
  the distance filter. On an empty board all cells are eligible before ranking.
- `evaluator`: callable `(board, root_player) -> finite float`, default `evaluate`.
  A replacement must preserve terminal utility (win positive, loss negative,
  draw zero), dominate heuristic scores with terminal scores, and be deterministic.
- `logger`: optional Python logger. Each decision emits an INFO record.

CLI values `--max-candidates 0` and `--radius 0` map to `None`. Set **both** to
zero to search every legal move; this becomes expensive on a 9×9 board.

Candidate order is identical in both agents: immediate wins, immediate blocks,
number of adjacent stones, distance to center, then row and column. The same
policy applies at MAX and MIN nodes, using the side moving at that node.
The strict cap can exclude important alternatives, including some blocks when
multiple threats exist. Filtering changes the tree and can change the decision;
Alpha-Beta preserves the MiniMax result on the same filtered tree.

## Search behavior

The root player is MAX; the opponent is MIN. Every score is measured from the
root player's perspective. MiniMax explores every candidate branch to the depth
limit or a terminal position. Alpha-Beta maintains alpha (MAX's lower bound) and
beta (MIN's upper bound), stopping when alpha >= beta. The algorithms use separate
recursive implementations; common configuration and instrumentation are reused
through inheritance. Equal scores keep the first move in the deterministic order.

The evaluator scores unblocked five-cell windows, including gapped threats;
contiguous runs with open ends; and a small center bonus. Terminal scores are
+1,000,000 / -1,000,000 / 0; nonterminal scores are clamped to half that magnitude.
There is no time cutoff, iterative deepening, cache or transposition table.
A larger requested depth is always searched unless a terminal state is reached.

## Statistics and comparisons

`last_stats` contains the chosen move, configured depth, maximum depth actually
reached, elapsed seconds, visited nodes, leaf nodes, cutoff events and root score.
Timing includes candidate generation, copying and evaluation, excludes writing
the final log record. Node counts include the root and each recursive search call;
they exclude tactical checks during candidate ordering. Each call resets stats.
`cutoffs` counts events with at least one unsearched sibling, not skipped subtrees'
unknown node counts. Random/human agents report zero search nodes and depth.

The comparison script checks identical moves and scores and no increase in
Alpha-Beta's node count. It alternates execution order and writes all measurements
to CSV. Included CSV files are measured results from this execution environment,
not estimates. See [docs/RESULTS.md](docs/RESULTS.md).

For integration contracts and adding MCTS or a GUI adapter, see
[docs/INTERFACES.md](docs/INTERFACES.md).
