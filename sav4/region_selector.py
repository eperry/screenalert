"""
Region selector module for Screen Region Monitor.

Provides a tkinter-based UI for users to select a region of the screen.
"""

import tkinter as tk
from typing import Tuple, Optional

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
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.1)  # 90% transparent overlay
        self.canvas = tk.Canvas(self, cursor="cross", bg="gray", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.start_x = self.start_y = self.end_x = self.end_y = 0
        self.rect = None
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.bind_events()
        self.update_screen_geometry()
        self.deiconify()

    def update_screen_geometry(self) -> None:
        """Set the window to cover the entire screen."""
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

    def bind_events(self) -> None:
        """Bind mouse events for region selection."""
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.bind("<Escape>", lambda e: self.cancel())

    def on_mouse_down(self, event: tk.Event) -> None:
        """Handle mouse button press event."""
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2, dash=(2, 2)
        )

    def on_mouse_drag(self, event: tk.Event) -> None:
        """Handle mouse drag event to update the selection rectangle."""
        if self.rect:
            self.end_x, self.end_y = event.x, event.y
            self.canvas.coords(self.rect, self.start_x, self.start_y, self.end_x, self.end_y)

    def on_mouse_up(self, event: tk.Event) -> None:
        """Handle mouse button release event to finalize the region."""
        if self.rect:
            self.end_x, self.end_y = event.x, event.y
            x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
            x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
            self.region = (x1, y1, x2, y2)
            self.destroy()

    def cancel(self) -> None:
        """Cancel the selection and close the window."""
        self.region = None
        self.destroy()

    def show(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Show the region selector window and block until a region is selected or cancelled.

        Returns:
            A tuple (left, top, right, bottom) of the selected region, or None if cancelled.
        """
        self.grab_set()
        self.wait_window()
        return self.region