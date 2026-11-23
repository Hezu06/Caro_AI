"""
Điểm khởi chạy chính của dự án Caro AI 9x9.
Mặc định mở giao diện đồ họa (CustomTkinter GUI).
Truyền cờ --cli nếu muốn chạy giao diện dòng lệnh (CLI).
"""
import sys


def main():
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        from src.ui.cli import main as cli_main
        cli_main()
    else:
        from src.ui.gui_customtkinter import run_gui
        run_gui()


if __name__ == "__main__":
    main()
