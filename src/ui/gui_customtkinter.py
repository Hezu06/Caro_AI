"""
GUI CustomTkinter: Giao diện đồ họa bàn cờ Caro 9x9 tích hợp các Agent.
Tuân thủ toàn bộ hợp đồng trong docs/INTERFACES.md.
"""
from __future__ import annotations

import customtkinter as ctk
import tkinter as tk
import threading
import time
from typing import Dict, Optional, Tuple, List

from src.config import (
    BOARD_SIZE, EMPTY, X, O,
    DEFAULT_DEPTH, DEFAULT_MAX_CANDIDATES, DEFAULT_CANDIDATE_RADIUS,
    opponent
)
from src.core.board import Board, BoardState, Move, DIRECTIONS
from src.core.game_engine import GameEngine
from src.agents import (
    BaseAgent, SearchStats,
    RandomAgent, MinimaxAgent, AlphaBetaAgent, HumanAgent
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Màu sắc giao diện bàn cờ
COLOR_BOARD_BG = "#eedab3"
COLOR_BOARD_LINE = "#8b7355"
COLOR_X = "#e74c3c"
COLOR_O = "#2980b9"
COLOR_LAST_MOVE = "#f1c40f"
COLOR_WIN_LINE = "#2ecc71"


def find_winning_line(board: BoardState, winner_player: int) -> List[Move]:
    """Tìm chuỗi >= 5 quân cờ liên tiếp của người thắng để highlight trên UI."""
    size = board.size
    for r in range(size):
        for c in range(size):
            if board.get_cell(r, c) != winner_player:
                continue
            for dr, dc in DIRECTIONS:
                # Bắt đầu từ quân đầu tiên của chuỗi
                pr, pc = r - dr, c - dc
                if 0 <= pr < size and 0 <= pc < size and board.get_cell(pr, pc) == winner_player:
                    continue
                line = []
                nr, nc = r, c
                while 0 <= nr < size and 0 <= nc < size and board.get_cell(nr, nc) == winner_player:
                    line.append((nr, nc))
                    nr += dr
                    nc += dc
                if len(line) >= board.win_length:
                    return line
    return []


class CaroGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Trí Tuệ Nhân Tạo - Cờ Caro 9x9 (MiniMax & Alpha-Beta)")
        self.geometry("1020x700")
        self.resizable(False, False)

        self.cell_size = 62
        self.board_pixel_size = self.cell_size * BOARD_SIZE

        self.engine = GameEngine()
        self.is_ai_thinking = False
        self.is_paused = False
        self.game_id = 0  # Dùng để vô hiệu hóa các worker thread cũ khi reset ván

        self._setup_ui()
        self._reset_game()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # 1. Bàn cờ Canvas (Bên trái)
        self.board_frame = ctk.CTkFrame(self, corner_radius=12)
        self.board_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        self.canvas = tk.Canvas(
            self.board_frame,
            width=self.board_pixel_size,
            height=self.board_pixel_size,
            bg=COLOR_BOARD_BG,
            highlightthickness=0,
            cursor="hand2"
        )
        self.canvas.pack(expand=True, padx=15, pady=15)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # 2. Bảng điều khiển Sidebar (Bên phải)
        self.sidebar = ctk.CTkFrame(self, width=380, corner_radius=12)
        self.sidebar.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        # Tiêu đề
        self.title_label = ctk.CTkLabel(
            self.sidebar, text="BẢNG ĐIỀU KHIỂN",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.pack(pady=(12, 8))

        # Chọn Agent X
        self.lbl_x = ctk.CTkLabel(self.sidebar, text="Bên X (Đi trước):", anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_x.pack(fill="x", padx=15)
        self.combo_x = ctk.CTkComboBox(
            self.sidebar,
            values=["Người chơi (Human)", "AlphaBetaAgent", "MinimaxAgent", "RandomAgent"]
        )
        self.combo_x.pack(fill="x", padx=15, pady=(0, 8))
        self.combo_x.set("Người chơi (Human)")

        # Chọn Agent O
        self.lbl_o = ctk.CTkLabel(self.sidebar, text="Bên O (Đi sau):", anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_o.pack(fill="x", padx=15)
        self.combo_o = ctk.CTkComboBox(
            self.sidebar,
            values=["Người chơi (Human)", "AlphaBetaAgent", "MinimaxAgent", "RandomAgent"]
        )
        self.combo_o.pack(fill="x", padx=15, pady=(0, 8))
        self.combo_o.set("AlphaBetaAgent")

        # Cấu hình MiniMax / Alpha-Beta Depth
        self.lbl_depth = ctk.CTkLabel(self.sidebar, text=f"Độ sâu tìm kiếm (Depth): {DEFAULT_DEPTH}", anchor="w")
        self.lbl_depth.pack(fill="x", padx=15)
        self.slider_depth = ctk.CTkSlider(self.sidebar, from_=1, to=4, number_of_steps=3, command=self._on_depth_change)
        self.slider_depth.set(DEFAULT_DEPTH)
        self.slider_depth.pack(fill="x", padx=15, pady=(0, 8))

        # Cấu hình Max Candidates
        self.lbl_cand = ctk.CTkLabel(self.sidebar, text=f"Số ứng viên tối đa (Max Candidates): {DEFAULT_MAX_CANDIDATES}", anchor="w")
        self.lbl_cand.pack(fill="x", padx=15)
        self.slider_cand = ctk.CTkSlider(self.sidebar, from_=6, to=24, number_of_steps=6, command=self._on_cand_change)
        self.slider_cand.set(DEFAULT_MAX_CANDIDATES)
        self.slider_cand.pack(fill="x", padx=15, pady=(0, 8))

        # Tốc độ AI Delay (giúp xem máy đấu máy dễ hơn)
        self.lbl_delay = ctk.CTkLabel(self.sidebar, text="Độ trễ mỗi nước AI: 0.20s", anchor="w")
        self.lbl_delay.pack(fill="x", padx=15)
        self.slider_delay = ctk.CTkSlider(self.sidebar, from_=0.0, to=1.0, number_of_steps=10, command=self._on_delay_change)
        self.slider_delay.set(0.2)
        self.slider_delay.pack(fill="x", padx=15, pady=(0, 10))

        # Khung các nút điều khiển
        self.btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=15, pady=(0, 8))

        self.btn_new_game = ctk.CTkButton(
            self.btn_frame, text="Ván Mới",
            font=ctk.CTkFont(weight="bold"),
            command=self._reset_game,
            height=34
        )
        self.btn_new_game.pack(side="left", expand=True, padx=(0, 4))

        self.btn_pause = ctk.CTkButton(
            self.btn_frame, text="Tạm Dừng",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#e67e22", hover_color="#d35400",
            command=self._toggle_pause,
            height=34
        )
        self.btn_pause.pack(side="left", expand=True, padx=(4, 0))

        # Nhãn hiển thị trạng thái lượt / kết quả
        self.lbl_status = ctk.CTkLabel(
            self.sidebar, text="Lượt: X",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f1c40f"
        )
        self.lbl_status.pack(fill="x", padx=15, pady=(2, 6))

        # Hộp nhật ký Log
        self.lbl_log = ctk.CTkLabel(self.sidebar, text="Nhật ký nước đi & Thống kê thuật toán:", anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_log.pack(fill="x", padx=15)

        self.log_box = ctk.CTkTextbox(self.sidebar, height=180, font=ctk.CTkFont(size=11))
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(2, 12))

    def _on_depth_change(self, value):
        self.lbl_depth.configure(text=f"Độ sâu tìm kiếm (Depth): {int(value)}")

    def _on_cand_change(self, value):
        self.lbl_cand.configure(text=f"Số ứng viên tối đa (Max Candidates): {int(value)}")

    def _on_delay_change(self, value):
        self.lbl_delay.configure(text=f"Độ trễ mỗi nước AI: {value:.2f}s")

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.configure(text="Tiếp Tục", fg_color="#27ae60", hover_color="#2ecc71")
            self._log(">> Ván đấu đã tạm dừng.")
        else:
            self.btn_pause.configure(text="Tạm Dừng", fg_color="#e67e22", hover_color="#d35400")
            self._log(">> Ván đấu tiếp tục.")
            self._check_and_trigger_ai()

    def _log(self, text: str):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def _create_agent(self, choice_text: str) -> Optional[BaseAgent]:
        """Tạo instance Agent riêng biệt cho mỗi bên (không dùng chung instance)."""
        depth = int(self.slider_depth.get())
        max_cand = int(self.slider_cand.get())
        radius = DEFAULT_CANDIDATE_RADIUS

        if "Human" in choice_text:
            return None  # Đại diện người chơi (xử lý trực tiếp qua sự kiện Canvas click)
        elif "Random" in choice_text:
            return RandomAgent()
        elif "AlphaBeta" in choice_text:
            return AlphaBetaAgent(depth=depth, max_candidates=max_cand, candidate_radius=radius)
        elif "Minimax" in choice_text:
            return MinimaxAgent(depth=depth, max_candidates=max_cand, candidate_radius=radius)
        return None

    def _reset_game(self):
        self.game_id += 1
        self.is_ai_thinking = False
        self.is_paused = False
        self.btn_pause.configure(text="Tạm Dừng", fg_color="#e67e22", hover_color="#d35400")

        self.engine = GameEngine()
        self.agents: Dict[int, Optional[BaseAgent]] = {
            X: self._create_agent(self.combo_x.get()),
            O: self._create_agent(self.combo_o.get())
        }

        name_x = self.combo_x.get().split()[0]
        name_o = self.combo_o.get().split()[0]
        self.lbl_status.configure(text=f"Lượt: {name_x} (X)", text_color=COLOR_X)
        self._log(f"\n=== VÁN MỚI: {name_x} (X) vs {name_o} (O) ===")
        self._draw_board()
        self._check_and_trigger_ai()

    def _draw_board(self):
        self.canvas.delete("all")
        cs = self.cell_size

        # 1. Vẽ các đường kẻ lưới 9x9
        for i in range(BOARD_SIZE + 1):
            self.canvas.create_line(i * cs, 0, i * cs, self.board_pixel_size, fill=COLOR_BOARD_LINE, width=1)
            self.canvas.create_line(0, i * cs, self.board_pixel_size, i * cs, fill=COLOR_BOARD_LINE, width=1)

        # 2. Highlight ô vừa đánh gần nhất
        if self.engine.history:
            last_record = self.engine.history[-1]
            lr, lc = last_record.move
            self.canvas.create_rectangle(
                lc * cs + 2, lr * cs + 2, (lc + 1) * cs - 2, (lr + 1) * cs - 2,
                fill=COLOR_LAST_MOVE, outline=""
            )

        # 3. Vẽ quân cờ X và O
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                val = self.engine.board.get_cell(r, c)
                if val == X:
                    pad = 14
                    self.canvas.create_line(c * cs + pad, r * cs + pad, (c + 1) * cs - pad, (r + 1) * cs - pad,
                                            fill=COLOR_X, width=4, capstyle="round")
                    self.canvas.create_line((c + 1) * cs - pad, r * cs + pad, c * cs + pad, (r + 1) * cs - pad,
                                            fill=COLOR_X, width=4, capstyle="round")
                elif val == O:
                    pad = 12
                    self.canvas.create_oval(c * cs + pad, r * cs + pad, (c + 1) * cs - pad, (r + 1) * cs - pad,
                                            outline=COLOR_O, width=4)

        # 4. Highlight chuỗi >= 5 quân thắng cuộc
        if self.engine.is_over and self.engine.winner is not None:
            win_line = find_winning_line(self.engine.board, self.engine.winner)
            for (wr, wc) in win_line:
                self.canvas.create_rectangle(
                    wc * cs + 3, wr * cs + 3, (wc + 1) * cs - 3, (wr + 1) * cs - 3,
                    outline=COLOR_WIN_LINE, width=4
                )

    def _on_canvas_click(self, event):
        if self.engine.is_over or self.is_ai_thinking or self.is_paused:
            return

        curr_p = self.engine.current_player
        if self.agents[curr_p] is not None:
            return  # Lượt của AI, bỏ qua click của người

        col = event.x // self.cell_size
        row = event.y // self.cell_size
        move = (row, col)

        if self.engine.board.is_legal(move):
            self._apply_move(move)

    def _apply_move(self, move: Move, stats: Optional[SearchStats] = None):
        curr_p = self.engine.current_player
        p_sym = "X" if curr_p == X else "O"

        # Thực hiện nước đi qua GameEngine
        self.engine.play(move)
        self._draw_board()

        # In log
        if stats is not None:
            log_line = (f"[{p_sym}] {stats.algorithm} -> ({move[0]}, {move[1]}) | "
                        f"Time: {stats.elapsed_seconds:.4f}s | "
                        f"Nodes: {stats.nodes_visited} | "
                        f"Cutoffs: {stats.cutoffs}")
            if stats.score is not None:
                log_line += f" | Score: {stats.score:.1f}"
            self._log(log_line)
        else:
            self._log(f"[{p_sym}] Người chơi -> ({move[0]}, {move[1]})")

        # Kiểm tra kết thúc ván
        if self.engine.is_over:
            if self.engine.winner is None:
                self.lbl_status.configure(text="KẾT QUẢ: HÒA CỜ (ĐẦY BÀN)!", text_color="#f39c12")
                self._log("=== KẾT THÚC: HÒA CỜ ===")
            else:
                win_sym = "X" if self.engine.winner == X else "O"
                win_name = "X" if self.engine.winner == X else "O"
                self.lbl_status.configure(text=f"CHIẾN THẮNG: {win_sym}!", text_color=COLOR_WIN_LINE)
                self._log(f"=== CHIẾN THẮNG: BÊN {win_sym} ĐẠT 5 QUÂN LIÊN TIẾP! ===")
            return

        # Cập nhật lượt người tiếp theo
        next_p = self.engine.current_player
        next_sym = "X" if next_p == X else "O"
        color = COLOR_X if next_p == X else COLOR_O
        agent_obj = self.agents[next_p]
        agent_name = "Người chơi" if agent_obj is None else type(agent_obj).__name__
        self.lbl_status.configure(text=f"Lượt: {agent_name} ({next_sym})", text_color=color)

        self._check_and_trigger_ai()

    def _check_and_trigger_ai(self):
        if self.engine.is_over or self.is_paused:
            return

        curr_p = self.engine.current_player
        curr_agent = self.agents[curr_p]

        if curr_agent is not None and not self.is_ai_thinking:
            self.is_ai_thinking = True
            delay = float(self.slider_delay.get())
            # Bản sao an toàn của board theo hợp đồng docs/INTERFACES.md
            board_copy = self.engine.board.clone()
            current_game_id = self.game_id

            threading.Thread(
                target=self._ai_worker,
                args=(curr_agent, board_copy, curr_p, current_game_id, delay),
                daemon=True
            ).start()

    def _ai_worker(self, agent: BaseAgent, board_snapshot: BoardState, player: int, game_id: int, delay: float):
        if delay > 0:
            time.sleep(delay)

        move = agent.get_move(board_snapshot, player)
        stats = agent.last_stats

        def callback():
            if self.game_id != game_id or self.engine.is_over:
                self.is_ai_thinking = False
                return
            self.is_ai_thinking = False
            if move is not None and self.engine.board.is_legal(move):
                self._apply_move(move, stats)

        self.after(10, callback)


def run_gui():
    app = CaroGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
