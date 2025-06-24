"""
Timer management module for Screen Region Monitor.

Defines TimerItem and TimersManager classes for timer logic.ogic.
"""

from typing import Callable, List, Optional, Dict, Anyrt Optional, List
import threading, ImageTk
import tkinter as tk
from tkinter import ttk
from tkinter.simpledialog import Dialogth, height, color="#fff", bgcolor=None, font_size=18):
BA", (width, height), bgcolor or (0, 0, 0, 0))
class TimerItem:    draw = ImageDraw.Draw(img)
    """
    Represents a countdown timer. font = ImageFont.truetype("arial.ttf", font_size)

    Args:        font = ImageFont.load_default()
        name: The name of the timer.sattr(draw, "textbbox"):
        seconds: The total countdown time in seconds. text, font=font)
        auto_restart: Whether the timer should auto-restart when finished.

    Attributes:    else:
        name: Timer name.dth, text_height = font.getsize(text)
        total_seconds: Total countdown time in seconds.th) // 2
        remaining: Remaining time in seconds.
        running: Whether the timer is currently running.olor)
        auto_restart: Whether the timer should auto-restart.
        mute_sound: Whether to mute sound for this timer.
        mute_tts: Whether to mute TTS for this timer.
        on_finish: Optional callback to call when timer finishes.
    """
al: int,
    def __init__(self, name: str, seconds: int, auto_restart: bool = False) -> None:    warning_threshold: float,
        self.name = name
        self.initial_seconds = seconds
        self.remaining = seconds
        self.auto_restart = auto_restart
        self.running = True
        self.mute_sound = False a timer row based on warning and alert thresholds.
        self.mute_tts = False

    def tick(self) -> None:        remaining: Seconds left on the timer.
        """s for the timer.
        Decrement the timer by one second if running.ning_threshold: Fraction (0-1) for warning color.
        Calls on_finish if the timer reaches zero.or.
        """FFD700").
        if self.running and self.remaining > 0:rt_color: Color for alert (e.g., "#FF3333").
            self.remaining -= 1
        if self.running and self.remaining == 0 and self.auto_restart:
            self.remaining = self.initial_seconds

    def toggle_pause(self) -> None:    if total == 0:
        """
        Toggle the running state of the timer._left = remaining / total
        """
        if self.running:urn alert_color
            self.running = Falsearning_threshold:
        else:
            if self.remaining == 0:ne
                self.remaining = self.initial_seconds
            self.running = True

    def to_dict(self) -> dict:    text: str,
        """Serialize timer to a dictionary for saving to config."""
        return {
            "name": self.name,
            "seconds": self.initial_seconds,
            "remaining": self.remaining,
            "auto_restart": self.auto_restart,
            "running": self.running,
            "mute_sound": self.mute_sound,ical) in the given canvas, using the provided font size.
            "mute_tts": self.mute_tts,
        }
tatus = create_rotated_text_image(
    @classmethod        text,
    def from_dict(cls, data: dict) -> "TimerItem":2 * margin,
        """Create a TimerItem from a dictionary."""
        timer = cls(data["name"], data["seconds"], data.get("auto_restart", False))
        timer.remaining = data.get("remaining", data["seconds"])
        timer.running = False  # Always start paused when loading from config
        timer.mute_sound = data.get("mute_sound", False)
        timer.mute_tts = data.get("mute_tts", False)
        return timer

class TimersManager:        height // 2,
    """er",
    Manages multiple TimerItem instances. image=imgtk

    Methods:    # Prevent garbage collection
        add_timer: Add a new timer.asattr(render_status_rotated, "_img_refs"):
        remove_timer: Remove a timer by index.refs = []
        get_timers: Get a list of all timers.tk)
        tick_all: Advance all running timers by one tick.
    """
ds: List[str],
    def __init__(self) -> None:    width: int,
        self.timers: List[TimerItem] = []

    def add_timer(self, name: str, seconds: int, auto_restart: bool = False) -> None:    margin: int = 2
        """
        Add a new timer.
font size that allows all given words to fit (rotated) in the box.
        Args:    """
            name: The timer name.import ImageFont, ImageDraw, Image
            seconds: The countdown time in seconds.t
            auto_restart: Whether the timer should auto-restart.-1):

        Returns:        for word in words:
            The created TimerItem.
        """ruetype(font_path, font_size)
        timer = TimerItem(name, seconds, auto_restart) except Exception:
        self.timers.append(timer)
e to measure
    def remove_timer(self, idx: int) -> None:            img = Image.new("RGBA", (width, height))
        """
        Remove a timer by its index. if hasattr(draw, "textbbox"):
((0, 0), word, font=font)
        Args:                text_width = bbox[2] - bbox[0]
            idx: The index of the timer to remove.   text_height = bbox[3] - bbox[1]
        """
        if 0 <= idx < len(self.timers):     text_width, text_height = font.getsize(word)
            del self.timers[idx]ght swap
 margin > width or text_width + 2 * margin > height:
    def get_timers(self) -> List[TimerItem]:                fits = False
        """
        Get a list of all timers.fits:

        Returns:    return min_font
            A list of TimerItem objects.
        """
        return self.timerstr,

    def tick_all(self) -> None:    height: int,
        """I",
        Advance all running timers by one tick (one second).ight: str = "bold",
        """
        for timer in self.timers:
            timer.tick()
font size that allows the rotated text to fit in the given box.
    def to_list(self) -> list:
        """Return a list of timer dicts for saving to config."""
        return [timer.to_dict() for timer in self.timers]

    def load_from_list(self, timer_dicts: list) -> None:        height: The height of the box.
        """Load timers from a list of dicts (all paused)."""
        self.timers = [TimerItem.from_dict(d) for d in timer_dicts]

class AddTimerDialog(Dialog):
    """
    Dialog for adding a new timer. The maximum font size that fits.
    Returns (name, seconds, auto_restart) as result.
    """
    def body(self, master: tk.Tk) -> tk.Widget:t.withdraw()
        ttk.Label(master, text="Timer Name:").grid(row=0, column=0, sticky="e")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(master, textvariable=self.name_var)t_weight)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
nt, anchor="nw", angle=90)
        ttk.Label(master, text="Seconds:").grid(row=1, column=0, sticky="e")        bbox = canvas.bbox(text_id)
        self.seconds_var = tk.StringVar()
        self.seconds_entry = ttk.Entry(master, textvariable=self.seconds_var)
        self.seconds_entry.grid(row=1, column=1, padx=5, pady=5)

        self.auto_restart_var = tk.BooleanVar()            if text_width + margin <= width and text_height + margin <= height:
        self.auto_restart_check = ttk.Checkbutton(
            master, text="Auto-Restart", variable=self.auto_restart_var
        )
        self.auto_restart_check.grid(row=2, column=0, columnspan=2, pady=5)n 8  # fallback minimum        return self.name_entry    def apply(self) -> None:        name = self.name_var.get().strip()        seconds = self.seconds_var.get().strip()        auto_restart = self.auto_restart_var.get()        self.result = (name, seconds, auto_restart)__all__ = ["TimersManager", "TimerItem", "AddTimerDialog"]