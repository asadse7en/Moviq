import ctypes
import tkinter as tk

from . import resource
from .ui.app import App, HAVE_DND, TkinterDnD


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "moviq.app",
        )
    except (AttributeError, OSError):
        pass

    root = TkinterDnD.Tk() if HAVE_DND else tk.Tk()
    try:
        root._moviq_icon = tk.PhotoImage(
            file=resource("assets/moviq-icon-256.png"),
        )
        root.iconphoto(True, root._moviq_icon)
    except (OSError, tk.TclError):
        pass
    app = App(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_close()


if __name__ == "__main__":
    main()
