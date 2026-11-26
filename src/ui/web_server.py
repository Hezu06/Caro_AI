"""
Web Server cho Giao diện Hand-Drawn Sketchbook Caro 9x9.
Sử dụng thư viện chuẩn http.server (không phụ thuộc package ngoài).
Kết nối giao diện web với AlphaBetaAgent, MinimaxAgent, RandomAgent và MCTSAgent.
"""
import os
import json
import socket
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from src.config import X, O, EMPTY, BOARD_SIZE, DEFAULT_DEPTH, DEFAULT_MAX_CANDIDATES
from src.core.board import Board
from src.agents import AlphaBetaAgent, MinimaxAgent, RandomAgent
from src.agents.mcts_agent import MCTSAgent

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class CaroWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        """Override để xử lý favicon và thêm no-cache headers."""
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        # Thêm Cache-Control để tránh browser cache file cũ
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/api/move":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
                grid_data = data.get("board")  # 9x9 array, X=1, O=-1, EMPTY=0
                player = int(data.get("player", O))
                algorithm = data.get("algorithm", "alpha-beta").lower()
                depth = int(data.get("depth", DEFAULT_DEPTH))
                max_cand = data.get("max_candidates", DEFAULT_MAX_CANDIDATES)
                if max_cand is not None:
                    max_cand = int(max_cand)

                # Khởi tạo bàn cờ Python
                board = Board(size=BOARD_SIZE, grid=grid_data)

                # Chọn Agent tương ứng
                if algorithm in ("alpha-beta", "alphabeta"):
                    agent = AlphaBetaAgent(depth=depth, max_candidates=max_cand)
                elif algorithm == "minimax":
                    agent = MinimaxAgent(depth=depth, max_candidates=max_cand)
                elif algorithm == "random":
                    agent = RandomAgent()
                elif algorithm == "mcts":
                    iterations = data.get("iterations", 300)
                    exploration = data.get("exploration", 0.65)
                    if type(exploration) not in (int, float):
                        raise ValueError("exploration must be a finite non-negative number")
                    agent = MCTSAgent(iterations=iterations, exploration=exploration)
                else:
                    agent = AlphaBetaAgent(depth=depth, max_candidates=max_cand)

                # Tính toán nước đi
                move = agent.get_move(board, player)
                stats = agent.last_stats.to_dict()

                response = {
                    "success": True,
                    "move": [move[0], move[1]] if move else None,
                    "stats": stats
                }
                self._send_json(response, 200)

            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 400)
        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Ẩn log GET tĩnh để terminal gọn gàng, chỉ in khi cần
        if args and isinstance(args[0], str) and "POST /api/move" in args[0]:
            print(f"[Caro Web Server] {args[0]} - Status {args[1]}")


def find_free_port(start_port: int = 8080) -> int:
    port = start_port
    while port < start_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1
    return start_port


def run_web_ui(port: int = 8080):
    port = find_free_port(port)
    server = HTTPServer(("127.0.0.1", port), CaroWebHandler)
    url = f"http://localhost:{port}"

    print(f"\n{'='*60}")
    print(f"CARO 9x9 SKETCHBOOK UI ĐÃ KHỞI ĐỘNG THÀNH CÔNG!")
    print(f"Đang mở trình duyệt tại: {url}")
    print(f"Nhấn Ctrl + C trên terminal để dừng server.")
    print(f"{'='*60}\n")

    # Mở trình duyệt
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Caro Web Server] Đã dừng server.")
        server.server_close()


if __name__ == "__main__":
    run_web_ui()
