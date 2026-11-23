"""Run with: python -m experiments.compare_search --depth 2 --repeats 3."""
import argparse
import csv
from pathlib import Path

from src.agents import AlphaBetaAgent, MinimaxAgent
from src.core import GameEngine


POSITIONS = {
    "opening": [(4, 4), (4, 5)],
    "middle": [(4, 4), (3, 4), (4, 5), (4, 3), (5, 5), (3, 3)],
    "threat": [(4, 1), (0, 0), (4, 2), (0, 1), (4, 3), (1, 0), (4, 4)],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--max-candidates", type=int, default=12, help="0 means unlimited")
    parser.add_argument("--radius", type=int, default=2, help="0 disables proximity filtering")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("experiments/results/search_comparison.csv"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    rows = []
    for name, moves in POSITIONS.items():
        engine = GameEngine()
        for move in moves:
            engine.play(move)
        for repeat in range(args.repeats):
            pair = {}
            # Alternate execution order to reduce order-related timing bias.
            classes = (MinimaxAgent, AlphaBetaAgent) if repeat % 2 == 0 else (AlphaBetaAgent, MinimaxAgent)
            for cls in classes:
                agent = cls(args.depth, args.max_candidates or None, args.radius or None)
                agent.get_move(engine.board, engine.current_player)
                stats = agent.last_stats.to_dict()
                pair[cls.__name__] = stats
                rows.append(dict(position=name, repeat=repeat,
                                 player=engine.current_player,
                                 max_candidates=args.max_candidates,
                                 candidate_radius=args.radius, **stats))
            mm, ab = pair["MinimaxAgent"], pair["AlphaBetaAgent"]
            assert mm["selected_move"] == ab["selected_move"]
            assert mm["score"] == ab["score"]
            assert ab["nodes_visited"] <= mm["nodes_visited"]
            reduction = 100 * (1 - ab["nodes_visited"] / mm["nodes_visited"])
            print(f"{name:8} run={repeat} move={mm['selected_move']} "
                  f"nodes={mm['nodes_visited']} -> {ab['nodes_visited']} "
                  f"({reduction:.1f}% fewer) "
                  f"seconds={mm['elapsed_seconds']:.4f} -> {ab['elapsed_seconds']:.4f}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
