"""
Timer management module for Screen Region Monitor.

Defines TimerItem and TimersManager classes for timer logic.
"""

import threading
from typing import Callable, List, Optional
import tkinter as tk
from tkinter import ttk
from tkinter.simpledialog import Dialog
from typing import List

class TimerItem:
    """
    Represents a countdown timer.

    Args:
        name: The name of the timer.
        seconds: The total countdown time in seconds.
        auto_restart: Whether the timer should auto-restart when finished.

    Attributes:
        name: Timer name.
        total_seconds: Total countdown time in seconds.
        remaining: Remaining time in seconds.
        running: Whether the timer is currently running.
        auto_restart: Whether the timer should auto-restart.
        mute_sound: Whether to mute sound for this timer.
        mute_tts: Whether to mute TTS for this timer.
        on_finish: Optional callback to call when timer finishes.
    """

    def __init__(self, name: str, seconds: int, auto_restart: bool = False) -> None:
        self.name = name
        self.initial_seconds = seconds
        self.remaining = seconds
        self.auto_restart = auto_restart
        self.running = True
        self.mute_sound = False
        self.mute_tts = False

    def tick(self) -> None:
        """
        Decrement the timer by one second if running.
        Calls on_finish if the timer reaches zero.
        """
        if self.running and self.remaining > 0:
            self.remaining -= 1
        if self.running and self.remaining == 0 and self.auto_restart:
            self.remaining = self.initial_seconds

    def toggle_pause(self) -> None:
        """
        Toggle the running state of the timer.
        """
        if self.running:
            self.running = False
        else:
            if self.remaining == 0:
                self.remaining = self.initial_seconds
            self.running = True

    def to_dict(self) -> dict:
        """Serialize timer to a dictionary for saving to config."""
        return {
            "name": self.name,
            "seconds": self.initial_seconds,
            "remaining": self.remaining,
            "auto_restart": self.auto_restart,
            "running": self.running,
            "mute_sound": self.mute_sound,
            "mute_tts": self.mute_tts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimerItem":
        """Create a TimerItem from a dictionary."""
        timer = cls(data["name"], data["seconds"], data.get("auto_restart", False))
        timer.remaining = data.get("remaining", data["seconds"])
        timer.running = False  # Always start paused when loading from config
        timer.mute_sound = data.get("mute_sound", False)
        timer.mute_tts = data.get("mute_tts", False)
        return timer

class TimersManager:
    """
    Manages multiple TimerItem instances.

    Methods:
        add_timer: Add a new timer.
        remove_timer: Remove a timer by index.
        get_timers: Get a list of all timers.
        tick_all: Advance all running timers by one tick.
    """

    def __init__(self) -> None:
        self.timers: List[TimerItem] = []

    def add_timer(self, name: str, seconds: int, auto_restart: bool = False) -> None:
        """
        Add a new timer.

        Args:
            name: The timer name.
            seconds: The countdown time in seconds.
            auto_restart: Whether the timer should auto-restart.

        Returns:
            The created TimerItem.
        """
        timer = TimerItem(name, seconds, auto_restart)
        self.timers.append(timer)

    def remove_timer(self, idx: int) -> None:
        """
        Remove a timer by its index.

        Args:
            idx: The index of the timer to remove.
        """
        if 0 <= idx < len(self.timers):
            del self.timers[idx]

    def get_timers(self) -> List[TimerItem]:
        """
        Get a list of all timers.

        Returns:
            A list of TimerItem objects.
        """
        return self.timers

    def tick_all(self) -> None:
        """
        Advance all running timers by one tick (one second).
        """
        for timer in self.timers:
            timer.tick()

    def to_list(self) -> list:
        """Return a list of timer dicts for saving to config."""
        return [timer.to_dict() for timer in self.timers]

    def load_from_list(self, timer_dicts: list) -> None:
        """Load timers from a list of dicts (all paused)."""
        self.timers = [TimerItem.from_dict(d) for d in timer_dicts]

class AddTimerDialog(Dialog):
    """
    Dialog for adding a new timer.
    Returns (name, seconds, auto_restart) as result.
    """
    def body(self, master: tk.Tk) -> tk.Widget:
        ttk.Label(master, text="Timer Name:").grid(row=0, column=0, sticky="e")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(master, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(master, text="Seconds:").grid(row=1, column=0, sticky="e")
        self.seconds_var = tk.StringVar()
        self.seconds_entry = ttk.Entry(master, textvariable=self.seconds_var)
        self.seconds_entry.grid(row=1, column=1, padx=5, pady=5)

        self.auto_restart_var = tk.BooleanVar()
        self.auto_restart_check = ttk.Checkbutton(
            master, text="Auto-Restart", variable=self.auto_restart_var
        )
        self.auto_restart_check.grid(row=2, column=0, columnspan=2, pady=5)

        return self.name_entry

    def apply(self) -> None:
        name = self.name_var.get().strip()
        seconds = self.seconds_var.get().strip()
        auto_restart = self.auto_restart_var.get()
        self.result = (name, seconds, auto_restart)

__all__ = ["TimersManager", "TimerItem", "AddTimerDialog"]