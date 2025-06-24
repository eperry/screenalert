"""
Main module for the Screen Region Monitor application.
Handles the GUI and delegates business logic to supporting modules.
"""

import os
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import tkinter.simpledialog as simpledialog
from typing import Any, Optional, Tuple
from PIL import ImageTk

from .config import load_config, save_config
from .timers import TimersManager
from .region_selector import RegionSelector
from .sound import play_sound, speak_tts
from .screenshot import take_full_screenshot, crop_region, create_thumbnail
from sav4.utils import get_max_rotated_font_size

APP_TITLE = "Screen Region Monitor"
MONITOR_TAB_LABEL = "Monitoring"
REGIONS_TAB_LABEL = "Regions"
TIMERS_TAB_LABEL = "Timers"
SETTINGS_TAB_LABEL = "Settings"

THUMB_WIDTH = 120
THUMB_HEIGHT = 100

def main() -> None:
    """
    Main entry point for the Screen Region Monitor application.
    Sets up the GUI and event handlers.
    """
    config = load_config()
    regions = config.get("regions", [])
    timers_manager = TimersManager(config.get("timers", []))

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("900x700")

    # --- Settings Variables ---
    interval_var = tk.IntVar(value=config.get("interval", 1000))
    tick_loop_interval_var = tk.IntVar(value=config.get("tick_loop_interval", 500))

    # --- Notebook and Tabs ---
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    merged_tab = ttk.Frame(notebook)
    regions_tab = ttk.Frame(notebook)
    timers_tab = ttk.Frame(notebook)
    settings_tab = ttk.Frame(notebook)

    notebook.add(merged_tab, text=MONITOR_TAB_LABEL)
    notebook.add(regions_tab, text=REGIONS_TAB_LABEL)
    notebook.add(timers_tab, text=TIMERS_TAB_LABEL)
    notebook.add(settings_tab, text=SETTINGS_TAB_LABEL)

    # Set Monitoring tab as active
    notebook.select(merged_tab)

    # --- Monitoring Tab Example ---
    merged_frame = ttk.Frame(merged_tab)
    merged_frame.pack(fill=tk.BOTH, expand=True)

    img_refs = []

    def update_merged_display() -> None:
        """
        Update the Monitoring tab with current region thumbnails and statuses.
        """
        for widget in merged_frame.winfo_children():
            widget.destroy()
        full_img = take_full_screenshot()
        img_refs.clear()
        for idx, region in enumerate(regions):
            coords = region.get("coords")
            if not coords or len(coords) != 4:
                continue
            region_img = crop_region(full_img, coords)
            thumb_img = create_thumbnail(region_img, (THUMB_WIDTH, THUMB_HEIGHT))
            imgtk = ImageTk.PhotoImage(thumb_img)
            frame = ttk.Frame(merged_frame, padding=4, relief="raised")
            frame.pack(fill=tk.X, pady=2)
            canvas = tk.Canvas(frame, width=THUMB_WIDTH, height=THUMB_HEIGHT)
            canvas.create_image(0, 0, anchor="nw", image=imgtk)
            canvas.pack(side=tk.LEFT)
            img_refs.append(imgtk)
            name_label = ttk.Label(frame, text=region.get("name", f"Region {idx+1}"), font=("Segoe UI", 14, "bold"))
            name_label.pack(side=tk.LEFT, padx=10)
            edit_btn = ttk.Button(frame, text="✏️", width=3, command=lambda idx=idx: edit_monitor_name(idx))
            edit_btn.pack(side=tk.RIGHT, padx=5)

    def edit_monitor_name(idx: int) -> None:
        """
        Prompt the user to edit the monitor name for a region.
        Updates the name and saves to config.
        """
        if idx < len(regions):
            item = regions[idx]
            current_name = item.get("name", f"Region {idx+1}")
            new_name = simpledialog.askstring(
                "Edit Name", "Enter new region name:", initialvalue=current_name
            )
            if new_name and new_name.strip():
                item["name"] = new_name.strip()
                save_config(config)
                update_merged_display()

    # --- Settings Tab Example ---
    settings_frame = ttk.Frame(settings_tab)
    settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    ttk.Label(settings_frame, text="Screenshot Interval (ms):").pack(anchor="w")
    interval_spin = ttk.Spinbox(settings_frame, from_=100, to=10000, increment=100, textvariable=interval_var, width=7)
    interval_spin.pack(anchor="w")
    ttk.Label(settings_frame, text="Timer Tick Loop Interval (ms):").pack(anchor="w")
    tick_loop_spin = ttk.Spinbox(settings_frame, from_=100, to=5000, increment=100, textvariable=tick_loop_interval_var, width=7)
    tick_loop_spin.pack(anchor="w")

    def save_settings() -> None:
        """
        Save all settings to config.py.
        """
        config["interval"] = interval_var.get()
        config["tick_loop_interval"] = tick_loop_interval_var.get()
        save_config(config)

    # --- Monitoring Logic Example ---
    def check_alerts() -> None:
        """
        Periodically check all monitored regions for changes and trigger alerts.
        """
        # ... monitoring logic here ...
        root.after(interval_var.get(), check_alerts)

    def timers_tick_loop() -> None:
        """
        Periodically update timers and refresh the merged display.
        """
        changed = timers_manager.tick_all()
        if changed:
            update_merged_display()
        root.after(tick_loop_interval_var.get(), timers_tick_loop)

    update_merged_display()
    root.after(1000, check_alerts)
    timers_tick_loop()
    root.mainloop()

if __name__ == "__main__":
    main()

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
        self.attributes("-alpha", 0.3)  # 70% opaque, similar to V3
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
        """Handle mouse button press event."""
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2
        )

    def on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag event to update the region rectangle."""
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event: tk.Event) -> None:
        """Handle mouse button release event to finalize the region selection."""
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

