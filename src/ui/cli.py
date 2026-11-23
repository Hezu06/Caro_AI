"""Minimal runnable CLI; algorithm code has no console dependencies."""
import argparse
import logging

from src.agents import AlphaBetaAgent, HumanAgent, MinimaxAgent, RandomAgent
from src.core import BoardState, GameEngine, Move


def render(board: BoardState) -> None:
    print("   " + " ".join(str(c) for c in range(board.size)))
    for r in range(board.size):
        print(f"{r:2} " + " ".join({0: ".", 1: "X", -1: "O"}[board.get_cell(r, c)]
                                   for c in range(board.size)))


def read_move(board: BoardState, player: int) -> Move:
    while True:
        try:
            r, c = map(int, input(f"{'X' if player == 1 else 'O'}: row col > ").split())
            if (r, c) in board.legal_moves():
                return r, c
        except ValueError:
            pass
        print("Enter a legal row and column, e.g. 4 4.")


def main() -> None:
    parser = argparse.ArgumentParser(description="9x9 Caro, five or more wins")
    parser.add_argument("--x", choices=["human", "random", "minimax", "alpha-beta"], default="human")
    parser.add_argument("--o", choices=["human", "random", "minimax", "alpha-beta"], default="alpha-beta")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--max-candidates", type=int, default=12, help="0 disables cap")
    parser.add_argument("--radius", type=int, default=2, help="0 disables proximity filter")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log", help="Optional UTF-8 log file")
    args = parser.parse_args()
    if args.log:
        logging.basicConfig(filename=args.log, encoding="utf-8", level=logging.INFO)

    def make(name: str, seed: int):
        if name == "human":
            return HumanAgent(read_move)
        if name == "random":
            return RandomAgent(seed)
        cls = MinimaxAgent if name == "minimax" else AlphaBetaAgent
        return cls(depth=args.depth, max_candidates=args.max_candidates or None,
                   candidate_radius=args.radius or None)

    try:
        agents = {1: make(args.x, args.seed), -1: make(args.o, args.seed + 1)}
    except ValueError as exc:
        parser.error(str(exc))
    game = GameEngine()
    render(game.board)
    try:
        while not game.is_over:
            agent = agents[game.current_player]
            game.step(agent)
            render(game.board)
            print(agent.last_stats.to_dict())
    except (EOFError, KeyboardInterrupt):
        print("\nGame stopped.")
        return
    print("Draw" if game.winner is None else f"Winner: {'X' if game.winner == 1 else 'O'}")
