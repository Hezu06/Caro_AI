"""User interfaces."""
from .cli import main as run_cli
from .gui_customtkinter import run_gui

__all__ = ["run_cli", "run_gui"]
