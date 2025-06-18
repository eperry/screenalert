"""
Timer management module for Screen Region Monitor.

Defines TimerItem and TimersManager classes for timer logic.
"""

import threading
from typing import Callable, List, Optional

class TimerItem:
    """
    Represents a single timer.

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
        self.total_seconds = seconds
        self.remaining = seconds
        self.running = False
        self.auto_restart = auto_restart
        self.mute_sound = False
        self.mute_tts = False
        self._lock = threading.Lock()
        self.on_finish: Optional[Callable[['TimerItem'], None]] = None

    def start(self) -> None:
        """Start or resume the timer."""
        with self._lock:
            self.running = True

    def pause(self) -> None:
        """Pause the timer."""
        with self._lock:
            self.running = False

    def toggle_pause(self) -> None:
        """Toggle the running state of the timer."""
        with self._lock:
            self.running = not self.running

    def reset(self) -> None:
        """Reset the timer to its original duration and pause it."""
        with self._lock:
            self.remaining = self.total_seconds
            self.running = False

    def tick(self) -> None:
        """
        Decrement the timer by one second if running.
        Calls on_finish if the timer reaches zero.
        """
        with self._lock:
            if self.running and self.remaining > 0:
                self.remaining -= 1
                if self.remaining <= 0:
                    self.running = False
                    if self.on_finish:
                        self.on_finish(self)
                    if self.auto_restart:
                        self.remaining = self.total_seconds
                        self.running = True

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
        self._timers: List[TimerItem] = []
        self._lock = threading.Lock()

    def add_timer(self, name: str, seconds: int, auto_restart: bool = False) -> TimerItem:
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
        with self._lock:
            self._timers.append(timer)
        return timer

    def remove_timer(self, idx: int) -> None:
        """
        Remove a timer by its index.

        Args:
            idx: The index of the timer to remove.
        """
        with self._lock:
            if 0 <= idx < len(self._timers):
                del self._timers[idx]

    def get_timers(self) -> List[TimerItem]:
        """
        Get a list of all timers.

        Returns:
            A list of TimerItem objects.
        """
        with self._lock:
            return list(self._timers)

    def tick_all(self) -> None:
        """
        Advance all running timers by one tick (one second).
        """
        with self._lock:
            for timer in self._timers:
                timer.tick()