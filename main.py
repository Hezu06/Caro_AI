"""
Điểm khởi chạy chính của dự án Caro AI 9x9.
Mặc định mở giao diện Sketchbook Hand-Drawn (Web UI).
Sử dụng cờ --customtkinter để mở giao diện CustomTkinter.
"""
import sys


def main():
    if "--customtkinter" in sys.argv:
        from src.ui.gui_customtkinter import run_gui
        run_gui()
    else:
        from src.ui.web_server import run_web_ui
        run_web_ui()


if __name__ == "__main__":
    main()
