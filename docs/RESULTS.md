# Measured comparison

Python 3.12.14, Linux x86_64.

Three repetitions per position, candidate cap 12, radius 2; times below are medians.
The exact move histories are defined in `experiments/compare_search.py`.

| Depth | Position | MiniMax nodes | Alpha-Beta nodes | Fewer nodes | MiniMax ms | Alpha-Beta ms |
|---|---|---:|---:|---:|---:|---:|
| 2 | opening | 157 | 48 | 69.4% | 56.61 | 17.56 |
| 2 | middle | 157 | 64 | 59.2% | 55.89 | 22.96 |
| 2 | threat | 157 | 36 | 77.1% | 48.09 | 9.77 |
| 3 | opening | 1885 | 394 | 79.1% | 611.09 | 128.76 |
| 3 | middle | 1885 | 521 | 72.4% | 685.40 | 191.33 |
| 3 | threat | 1621 | 47 | 97.1% | 577.89 | 14.54 |

For every comparison the selected move and root score matched. Alpha-Beta
skipped branches once their bounds could no longer improve an ancestor decision.
The size of the reduction depends on the position and move order. The strong
reduction in the depth-3 threat position comes from examining tactical blocks
early and rapidly rejecting alternatives that permit a win.

These are illustrative search comparisons on three positions, not tournament
win-rate evidence. Timing varies by machine and load. Reduced node counts do
not guarantee the same proportional time improvement because move ranking,
board cloning and evaluation also cost time. The chosen moves remain limited
by the heuristic, depth horizon, radius filter and candidate cap.

Validation: 14 unittest methods passed, including independent exhaustive
depth-limited reference comparisons on seeded 3×3 positions for both sides,
terminal/draw rules, forced tactics, state preservation and engine integration.
The default 9×9 rules are tested in all four directions, with overlines and
both ends blocked.
