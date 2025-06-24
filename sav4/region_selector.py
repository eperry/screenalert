"""
Region selector module for Screen Region Monitor.

Provides a tkinter-based UI for users to select a region of the screen.
"""

import tkinter as tk
from typing import Optional, Tuple

class RegionSelector(tk.Toplevel):
    """
    A modal window that allows the user to select a rectangular region on the screen.

    Example usage:
        selector = RegionSelector(root)
        region = selector.show()
        if region:
            print("Selected region:", region)
    """

    def __init__(self, master: tk.Tk):
        """
        Initialize the region selector window.

        Args:
            master: The parent tkinter root or window.
        """
        super().__init__(master)
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.3)
        self.configure(bg='black')
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        self.canvas = tk.Canvas(self, cursor="cross", bg="gray", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.start_x = self.start_y = self.rect = None
        self.bind_events()
        self.deiconify()
        self.lift()
        self.focus_force()

    def bind_events(self) -> None:
        """Bind mouse and keyboard events for region selection."""
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.cancel())

    def on_press(self, event: tk.Event) -> None:
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2
        )

    def on_drag(self, event: tk.Event) -> None:
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event: tk.Event) -> None:
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        x1, y1 = int(self.start_x), int(self.start_y)
        x2, y2 = int(end_x), int(end_y)
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        self.region = (left, top, width, height)
        self.destroy()

    def cancel(self) -> None:
        """Cancel the selection and close the window."""
        self.region = None
        self.destroy()

    def show(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Show the region selector and wait for the user to select a region.

        Returns:
            The selected region as a tuple (left, top, width, height), or None if canceled.
        """
        self.grab_set()
        self.wait_window()
        return self.region