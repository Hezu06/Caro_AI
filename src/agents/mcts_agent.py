            # Expansion: try one new move, sampled uniformly without replacement.
            if node.untried_moves:
                index = self.rng.randrange(len(node.untried_moves))
                move = node.untried_moves.pop(index)
                simulation.place(move, current_player)
                current_player = opponent(current_player)
                child = _Node(simulation.legal_moves())
                node.children[move] = child
                node = child
                path.append(node)

            # Simulation: play both sides uniformly at random to the end.
            winner = self._rollout(simulation, current_player, node.untried_moves)
            reward = 0.5 if winner is None else float(winner == player)

            # Backpropagation: the same root-perspective reward updates the path.
            for visited in path:
                visited.visits += 1
                visited.value_sum += reward
            stats.nodes_visited += len(path) - 1
            stats.leaf_nodes += 1
            stats.depth_reached = max(stats.depth_reached, len(path) - 1)

        # Use visit count for the played move, with average reward as a tiebreak.
        move, best = max(
            root.children.items(),
            key=lambda item: (item[1].visits, item[1].value_sum / item[1].visits),
        )
        stats.selected_move = move
        stats.score = best.value_sum / best.visits
        stats.elapsed_seconds = perf_counter() - started
        return move

    def _select_child(self, node: _Node, root_turn: bool) -> tuple[Move, _Node]:
        log_parent_visits = log(node.visits)

        def uct(item: tuple[Move, _Node]) -> float:
            child = item[1]
            mean = child.value_sum / child.visits
            exploitation = mean if root_turn else 1.0 - mean
            return exploitation + self.exploration * sqrt(log_parent_visits / child.visits)

        # Every child received a visit when it was expanded.
        return max(node.children.items(), key=uct)

    def _rollout(self, board: BoardState, player: int, legal_moves: list[Move]) -> int | None:
        if not legal_moves:
            return board.winner()

        # Placements only remove available squares, so a shuffled list suffices.
        remaining = legal_moves.copy()
        self.rng.shuffle(remaining)
        for move in remaining:
            board.place(move, player)
            winner = board.winner()
            if winner is not None:
                return winner
            player = opponent(player)
        return None
