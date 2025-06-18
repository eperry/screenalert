"""
Main module for the Screen Region Monitor application.
Handles the GUI and delegates business logic to supporting modules.
"""

import os
import time
import uuid
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.simpledialog import Dialog
from typing import Any, Optional, Tuple

from PIL import Image, ImageTk
import numpy as np
from skimage.metrics import structural_similarity as ssim

from .config import load_config, save_config
from .timers import TimersManager, TimerItem
from .utils import get_timer_row_color, create_rotated_text_image
from .screenshot import capture_region, take_full_screenshot, crop_region
from .region_selector import RegionSelector
from .sound import play_sound, speak_tts

# User-facing strings for easy localization
APP_TITLE = "Screen Region Monitor"
TIMER_NAME_LABEL = "Timer Name"
TIME_LEFT_LABEL = "Time Left (s)"
PAUSE_LABEL = "Pause"
AUTO_RESTART_LABEL = "Auto-Restart"
MUTE_SOUND_LABEL = "Mute Sound"
MUTE_TTS_LABEL = "Mute TTS"
REMOVE_LABEL = ""
ADD_TIMER_LABEL = "Add Timer"
SETTINGS_TAB_LABEL = "Settings"
REGIONS_TAB_LABEL = "Regions"
TIMERS_TAB_LABEL = "Timers"

REGION_SHOTS_DIR = "region_shots"
os.makedirs(REGION_SHOTS_DIR, exist_ok=True)

def main() -> None:
    """
    Main entry point for the Screen Region Monitor application.
    Sets up the GUI and event handlers.
    """
    config = load_config()
    timers_manager = TimersManager()

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("1000x600")

    # --- Settings Variables ---
    warning_threshold_var = tk.DoubleVar(value=config.get("timer_warning_threshold", 0.10))
    warning_color_var = tk.StringVar(value=config.get("timer_warning_color", "#FFD700"))
    alert_threshold_var = tk.DoubleVar(value=config.get("timer_alert_threshold", 0.01))
    alert_color_var = tk.StringVar(value=config.get("timer_alert_color", "#FF3333"))
    timer_sound_var = tk.StringVar(value=config.get("timer_sound", ""))
    default_tts_var = tk.StringVar(value=config.get("default_tts", "Alert {name}"))
    interval_var = tk.IntVar(value=config.get("interval", 1000))
    highlight_time_var = tk.IntVar(value=config.get("highlight_time", 5))
    green_text_var = tk.StringVar(value=config.get("green_text", "Green"))
    green_color_var = tk.StringVar(value=config.get("green_color", "#080"))
    paused_text_var = tk.StringVar(value=config.get("paused_text", "Paused"))
    paused_color_var = tk.StringVar(value=config.get("paused_color", "#08f"))
    alert_text_var = tk.StringVar(value=config.get("alert_text", "Alert"))
    alert_color_var = tk.StringVar(value=config.get("alert_color", "#a00"))

    # --- Notebook Tabs ---
    notebook = ttk.Notebook(root)
    regions_tab = ttk.Frame(notebook)
    settings_tab = ttk.Frame(notebook)
    timers_tab = ttk.Frame(notebook)
    notebook.add(regions_tab, text=REGIONS_TAB_LABEL)
    notebook.add(settings_tab, text=SETTINGS_TAB_LABEL)
    notebook.add(timers_tab, text=TIMERS_TAB_LABEL)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # --- Settings Tab UI ---
    settings_frame = ttk.Frame(settings_tab, padding=10)
    settings_frame.pack(fill=tk.BOTH, expand=True)

    # --- 1. Global Settings Section ---
    global_frame = ttk.LabelFrame(settings_frame, text="Global Settings", padding=10)
    global_frame.pack(fill=tk.X, pady=(0, 10), anchor="n")

    ttk.Label(global_frame, text="Screenshot Interval (ms):").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    interval_spin = ttk.Spinbox(global_frame, from_=100, to=10000, increment=100, textvariable=interval_var, width=7)
    interval_spin.grid(row=0, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(global_frame, text="Highlight Time (s):").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    highlight_spin = ttk.Spinbox(global_frame, from_=1, to=60, increment=1, textvariable=highlight_time_var, width=7)
    highlight_spin.grid(row=1, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(global_frame, text="Default Alert Sound:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    default_sound_entry = ttk.Entry(global_frame, textvariable=timer_sound_var, width=25)
    default_sound_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
    def browse_default_sound():
        from tkinter import filedialog as fd
        file = fd.askopenfilename(title="Select Sound File", filetypes=[("Audio Files", "*.wav *.mp3 *.ogg"), ("All Files", "*.*")])
        if file:
            timer_sound_var.set(file)
    browse_default_btn = ttk.Button(global_frame, text="Browse...", command=browse_default_sound)
    browse_default_btn.grid(row=2, column=2, sticky="w", padx=2, pady=2)

    ttk.Label(global_frame, text="Default TTS Message:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
    default_tts_entry = ttk.Entry(global_frame, textvariable=default_tts_var, width=25)
    default_tts_entry.grid(row=3, column=1, sticky="w", padx=5, pady=2)

    # --- 2. Tab Level Settings Section ---
    tab_frame = ttk.LabelFrame(settings_frame, text="Tab Level Settings", padding=10)
    tab_frame.pack(fill=tk.X, pady=(0, 10), anchor="n")

    ttk.Label(tab_frame, text="Timer Warning Threshold (%)").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    warning_entry = ttk.Entry(tab_frame, textvariable=warning_threshold_var, width=10)
    warning_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(tab_frame, text="Timer Warning Color:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    warning_color_btn = ttk.Button(
        tab_frame,
        text="Pick Color",
        command=lambda: warning_color_var.set(colorchooser.askcolor()[1] or warning_color_var.get())
    )
    warning_color_btn.grid(row=1, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(tab_frame, text="Timer Alert Threshold (%)").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    alert_entry = ttk.Entry(tab_frame, textvariable=alert_threshold_var, width=10)
    alert_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(tab_frame, text="Timer Alert Color:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
    alert_color_btn = ttk.Button(
        tab_frame,
        text="Pick Color",
        command=lambda: alert_color_var.set(colorchooser.askcolor()[1] or alert_color_var.get())
    )
    alert_color_btn.grid(row=3, column=1, sticky="w", padx=5, pady=2)

    # --- 3. Timers and Selected Regions Section ---
    timer_region_frame = ttk.LabelFrame(settings_frame, text="Timers and Selected Regions", padding=10)
    timer_region_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10), anchor="n")

    # Green State
    ttk.Label(timer_region_frame, text="Normal State Text:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    green_text_entry = ttk.Entry(timer_region_frame, textvariable=green_text_var, width=15)
    green_text_entry.grid(row=0, column=1, sticky="w", padx=2, pady=2)
    ttk.Label(timer_region_frame, text="Color:").grid(row=0, column=2, sticky="e", padx=2, pady=2)
    green_color_btn = ttk.Button(timer_region_frame, text="Pick", width=8)
    green_color_btn.grid(row=0, column=3, sticky="w", padx=2, pady=2)
    def choose_green_color():
        color = colorchooser.askcolor(color=green_color_var.get())[1]
        if color:
            green_color_var.set(color)
    green_color_btn.config(command=choose_green_color)

    # Paused State
    ttk.Label(timer_region_frame, text="Paused State Text:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    paused_text_entry = ttk.Entry(timer_region_frame, textvariable=paused_text_var, width=15)
    paused_text_entry.grid(row=1, column=1, sticky="w", padx=2, pady=2)
    ttk.Label(timer_region_frame, text="Color:").grid(row=1, column=2, sticky="e", padx=2, pady=2)
    paused_color_btn = ttk.Button(timer_region_frame, text="Pick", width=8)
    paused_color_btn.grid(row=1, column=3, sticky="w", padx=2, pady=2)
    def choose_paused_color():
        color = colorchooser.askcolor(color=paused_color_var.get())[1]
        if color:
            paused_color_var.set(color)
    paused_color_btn.config(command=choose_paused_color)

    # Alert State
    ttk.Label(timer_region_frame, text="Alert State Text:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    alert_text_entry = ttk.Entry(timer_region_frame, textvariable=alert_text_var, width=15)
    alert_text_entry.grid(row=2, column=1, sticky="w", padx=2, pady=2)
    ttk.Label(timer_region_frame, text="Color:").grid(row=2, column=2, sticky="e", padx=2, pady=2)
    alert_color_btn = ttk.Button(timer_region_frame, text="Pick", width=8)
    alert_color_btn.grid(row=2, column=3, sticky="w", padx=2, pady=2)
    def choose_alert_color():
        color = colorchooser.askcolor(color=alert_color_var.get())[1]
        if color:
            alert_color_var.set(color)
    alert_color_btn.config(command=choose_alert_color)

    # --- Save Settings Button ---
    def save_settings() -> None:
        """
        Save all settings to config.
        """
        config["timer_warning_threshold"] = warning_threshold_var.get()
        config["timer_warning_color"] = warning_color_var.get()
        config["timer_alert_threshold"] = alert_threshold_var.get()
        config["timer_alert_color"] = alert_color_var.get()
        config["timer_sound"] = timer_sound_var.get()
        config["default_tts"] = default_tts_var.get()
        config["interval"] = interval_var.get()
        config["highlight_time"] = highlight_time_var.get()
        config["green_text"] = green_text_var.get()
        config["green_color"] = green_color_var.get()
        config["paused_text"] = paused_text_var.get()
        config["paused_color"] = paused_color_var.get()
        config["alert_text"] = alert_text_var.get()
        config["alert_color"] = alert_color_var.get()
        save_config(config)
        messagebox.showinfo("Settings", "Settings saved.")

    save_btn = ttk.Button(settings_frame, text="Save Settings", command=save_settings)
    save_btn.pack(pady=(10, 0))

    # --- Timers Tab ---
    timers_frame = ttk.Frame(timers_tab)
    timers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    timers_tree = ttk.Treeview(
        timers_frame,
        columns=("name", "remaining", "pause", "auto_restart", "mute_sound", "mute_tts", "remove"),
        show="headings",
        height=10
    )
    timers_tree.heading("name", text=TIMER_NAME_LABEL)
    timers_tree.heading("remaining", text=TIME_LEFT_LABEL)
    timers_tree.heading("pause", text=PAUSE_LABEL)
    timers_tree.heading("auto_restart", text=AUTO_RESTART_LABEL)
    timers_tree.heading("mute_sound", text=MUTE_SOUND_LABEL)
    timers_tree.heading("mute_tts", text=MUTE_TTS_LABEL)
    timers_tree.heading("remove", text=REMOVE_LABEL)
    timers_tree.column("pause", width=60, anchor="center", stretch=False)
    timers_tree.column("auto_restart", width=90, anchor="center", stretch=False)
    timers_tree.column("mute_sound", width=80, anchor="center", stretch=False)
    timers_tree.column("mute_tts", width=80, anchor="center", stretch=False)
    timers_tree.column("remove", width=40, anchor="center", stretch=False)
    timers_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    def refresh_timers_tree() -> None:
        """
        Refresh the timers treeview, updating row colors and values.
        """
        timers_tree.delete(*timers_tree.get_children())
        warning_threshold = warning_threshold_var.get() / 100.0
        alert_threshold = alert_threshold_var.get() / 100.0
        warning_color = warning_color_var.get()
        alert_color = alert_color_var.get()
        for idx, timer in enumerate(timers_manager.get_timers()):
            pause_text = "⏸️" if timer.running else "▶️"
            auto_restart_text = "☑" if timer.auto_restart else "☐"
            mute_sound_text = "🔇" if timer.mute_sound else "🔊"
            mute_tts_text = "🔇" if timer.mute_tts else "🗣️"
            row_color = get_timer_row_color(
                timer.remaining,
                timer.total_seconds,
                warning_threshold,
                alert_threshold,
                warning_color,
                alert_color
            )
            timers_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    timer.name,
                    timer.remaining,
                    pause_text,
                    auto_restart_text,
                    mute_sound_text,
                    mute_tts_text,
                    "❌"
                ),
                tags=(f"timer_row_{idx}",)
            )
            timers_tree.tag_configure(f"timer_row_{idx}", background=row_color or "")

    def on_timer_tree_click(event: Any) -> None:
        """
        Handle clicks on the timers treeview for pause, auto-restart, mute, and remove actions.
        """
        region = timers_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = timers_tree.identify_column(event.x)
        row = timers_tree.identify_row(event.y)
        if not row:
            return
        idx = int(row)
        timer = timers_manager.get_timers()[idx]
        if col == "#3":  # Pause column
            timer.toggle_pause()
            refresh_timers_tree()
        elif col == "#4":  # Auto-Restart column
            timer.auto_restart = not timer.auto_restart
            refresh_timers_tree()
        elif col == "#5":  # Mute Sound column
            timer.mute_sound = not timer.mute_sound
            refresh_timers_tree()
        elif col == "#6":  # Mute TTS column
            timer.mute_tts = not timer.mute_tts
            refresh_timers_tree()
        elif col == "#7":  # Remove column
            timers_manager.remove_timer(idx)
            refresh_timers_tree()

    timers_tree.bind("<Button-1>", on_timer_tree_click)

    def timer_finished(timer: TimerItem) -> None:
        """
        Callback for when a timer finishes. Plays sound and/or TTS if not muted.
        """
        if not timer.mute_sound and timer_sound_var.get():
            play_sound(timer_sound_var.get())
        if not timer.mute_tts:
            speak_tts(f"{timer.name} has finished")

    def assign_finish_callbacks() -> None:
        """
        Assign the finish callback to all timers.
        """
        for timer in timers_manager.get_timers():
            timer.on_finish = timer_finished

    class AddTimerDialog(Dialog):
        """
        Dialog for adding a new timer.
        """
        def body(self, master: tk.Widget) -> tk.Widget:
            tk.Label(master, text=TIMER_NAME_LABEL).grid(row=0, column=0, sticky="e")
            tk.Label(master, text=TIME_LEFT_LABEL).grid(row=1, column=0, sticky="e")
            self.name_var = tk.StringVar()
            self.seconds_var = tk.StringVar()
            self.auto_restart_var = tk.BooleanVar()
            self.name_entry = tk.Entry(master, textvariable=self.name_var)
            self.seconds_entry = tk.Entry(master, textvariable=self.seconds_var)
            self.auto_restart_cb = tk.Checkbutton(
                master, text=AUTO_RESTART_LABEL, variable=self.auto_restart_var
            )
            self.name_entry.grid(row=0, column=1, padx=5, pady=5)
            self.seconds_entry.grid(row=1, column=1, padx=5, pady=5)
            self.auto_restart_cb.grid(row=2, column=1, sticky="w", padx=5, pady=5)
            return self.name_entry  # initial focus

        def apply(self) -> None:
            self.result = (
                self.name_var.get(),
                self.seconds_var.get(),
                self.auto_restart_var.get()
            )

    def add_timer_prompt() -> None:
        """
        Prompt the user to add a new timer.
        """
        dialog = AddTimerDialog(timers_tab, title=ADD_TIMER_LABEL)
        if dialog.result:
            name, seconds, auto_restart = dialog.result
            if not name or not seconds:
                messagebox.showerror("Invalid Input", "Please enter both name and seconds.")
                return
            try:
                seconds = int(seconds)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number for seconds.")
                return
            timer = timers_manager.add_timer(name, seconds, auto_restart)
            timer.on_finish = timer_finished
            timer.start()
            refresh_timers_tree()

    add_timer_btn = ttk.Button(timers_frame, text=ADD_TIMER_LABEL, command=add_timer_prompt)
    add_timer_btn.pack(fill=tk.X, padx=5, pady=5, side=tk.RIGHT)

    def timers_tick_loop() -> None:
        """
        Periodically update timers and refresh the treeview.
        """
        timers_manager.tick_all()
        assign_finish_callbacks()
        refresh_timers_tree()
        timers_frame.after(1000, timers_tick_loop)

    timers_tick_loop()

    # --- Regions Tab ---
    regions = config.setdefault("regions", [])
    previous_screenshots = []

    # --- Controls at the Top ---
    controls_frame = ttk.Frame(regions_tab)
    controls_frame.pack(fill=tk.X, pady=(0, 10), anchor="n")

    def add_region() -> None:
        """
        Prompt the user to select a region and add it to the monitored list.
        """
        root.withdraw()
        region = RegionSelector(root).show()
        root.deiconify()
        if region and all(region):
            region_name = f"Region {len(regions)+1}"
            full_img = take_full_screenshot()
            cropped_img = crop_region(full_img, region)
            img_id = str(uuid.uuid4())
            img_path = os.path.join(REGION_SHOTS_DIR, f"region_{img_id}.png")
            cropped_img.save(img_path)
            regions.append({
                "coords": region,
                "name": region_name,
                "paused": False,
                "mute_sound": False,
                "mute_tts": False,
                "last_alert_time": 0,
                "thumbnail_path": img_path
            })
            previous_screenshots.append(cropped_img)
            save_config(config)
            update_region_display()

    add_btn = ttk.Button(controls_frame, text="➕ Add Region", command=add_region)
    add_btn.pack(side=tk.LEFT, padx=5)

    all_paused = tk.BooleanVar(value=False)
    all_muted_sound = tk.BooleanVar(value=False)
    all_muted_tts = tk.BooleanVar(value=False)

    def pause_all_alerts(paused: bool) -> None:
        """
        Pause or resume all region alerts.

        Args:
            paused: If True, pause all alerts; if False, resume all.
        """
        for region in regions:
            region["paused"] = paused
        update_region_display()
        logging.info("All alerts %s.", "paused" if paused else "resumed")

    def toggle_pause_all() -> None:
        """
        Toggle the pause state for all alerts and update the button label.
        """
        new_state = not all_paused.get()
        all_paused.set(new_state)
        pause_all_alerts(new_state)
        pause_all_btn.config(
            text="Resume All" if new_state else "Pause All"
        )

    pause_all_btn = ttk.Button(
        controls_frame,
        text="Pause All",
        command=toggle_pause_all
    )
    pause_all_btn.pack(side=tk.LEFT, padx=5)

    def mute_all_sound(mute: bool) -> None:
        """
        Mute or unmute sound for all regions.

        Args:
            mute: If True, mute all sound; if False, unmute all.
        """
        for region in regions:
            region["mute_sound"] = mute
        update_region_display()
        logging.info("All sound %s.", "muted" if mute else "unmuted")

    def toggle_mute_all_sound() -> None:
        """
        Toggle mute state for all region sounds and update the button label.
        """
        new_state = not all_muted_sound.get()
        all_muted_sound.set(new_state)
        mute_all_sound(new_state)
        mute_all_sound_btn.config(
            text="Unmute All Sound" if new_state else "Mute All Sound"
        )

    mute_all_sound_btn = ttk.Button(
        controls_frame,
        text="Mute All Sound",
        command=toggle_mute_all_sound
    )
    mute_all_sound_btn.pack(side=tk.LEFT, padx=5)

    def mute_all_tts(mute: bool) -> None:
        """
        Mute or unmute TTS for all regions.

        Args:
            mute: If True, mute all TTS; if False, unmute all.
        """
        for region in regions:
            region["mute_tts"] = mute
        update_region_display()
        logging.info("All TTS %s.", "muted" if mute else "unmuted")

    def toggle_mute_all_tts() -> None:
        """
        Toggle mute state for all region TTS and update the button label.
        """
        new_state = not all_muted_tts.get()
        all_muted_tts.set(new_state)
        mute_all_tts(new_state)
        mute_all_tts_btn.config(
            text="Unmute All TTS" if new_state else "Mute All TTS"
        )

    mute_all_tts_btn = ttk.Button(
        controls_frame,
        text="Mute All TTS",
        command=toggle_mute_all_tts
    )
    mute_all_tts_btn.pack(side=tk.LEFT, padx=5)

    # --- Regions List ---
    regions_frame_outer = ttk.LabelFrame(regions_tab, text="Monitored Regions", padding=10)
    regions_frame_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    canvas = tk.Canvas(regions_frame_outer, borderwidth=0, background="#222", highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    regions_frame = ttk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=regions_frame, anchor="nw", tags="regions_window")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    def on_canvas_configure(event):
        canvas.itemconfig("regions_window", width=event.width)
    regions_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)
    regions_frame.grid_columnconfigure(0, weight=1)

    region_widgets = []

    def update_region_display():
        """
        Update all region widgets: status, thumbnail, controls.
        """
        full_img = take_full_screenshot()
        update_region_display.img_refs = []

        # Ensure region_widgets matches regions
        while len(region_widgets) < len(regions):
            rf = ttk.Frame(regions_frame, padding=4, relief="raised")
            rf.grid_columnconfigure(0, minsize=28, weight=0)
            rf.grid_columnconfigure(1, minsize=120, weight=0)
            rf.grid_columnconfigure(2, weight=1)
            rf.grid_columnconfigure(3, weight=0)
            rf.grid_columnconfigure(4, weight=0)

            # Status canvas
            status_canvas = tk.Canvas(rf, width=48, height=100, highlightthickness=0, bd=0)
            status_canvas.grid(row=0, column=0, rowspan=3, sticky="nsw", padx=(0, 8), pady=0)

            # Thumbnail canvas
            img_canvas = tk.Canvas(rf, width=120, height=100, highlightthickness=0, bd=0, bg="#111")
            img_canvas.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=0, pady=0)

            # Name label
            name_label = ttk.Label(rf)
            name_label.grid(row=0, column=2, sticky="w", padx=(0, 8))

            # Controls frame
            controls_frame = ttk.Frame(rf)
            controls_frame.grid(row=0, column=3, rowspan=3, sticky="e", padx=2)
            controls_frame.grid_columnconfigure(0, weight=1)

            # Pause button
            pause_btn = ttk.Button(controls_frame, width=10)
            pause_btn.grid(row=0, column=0, sticky="ew", pady=2)

            # Mute sound button
            mute_sound_btn = ttk.Button(controls_frame, width=14)
            mute_sound_btn.grid(row=1, column=0, sticky="ew", pady=2)

            # Mute TTS button
            mute_tts_btn = ttk.Button(controls_frame, width=14)
            mute_tts_btn.grid(row=2, column=0, sticky="ew", pady=2)

            # Remove button
            remove_btn = ttk.Button(rf, text="❌", width=3)
            remove_btn.grid(row=0, column=4, rowspan=3, sticky="e", padx=(8,2), pady=2)

            rf.grid(row=len(region_widgets), column=0, sticky="ew", padx=8, pady=6)
            region_widgets.append({
                "frame": rf,
                "status_canvas": status_canvas,
                "img_canvas": img_canvas,
                "name_label": name_label,
                "pause_btn": pause_btn,
                "mute_sound_btn": mute_sound_btn,
                "mute_tts_btn": mute_tts_btn,
                "remove_btn": remove_btn,
            })

        # Remove extra widgets if regions were deleted
        while len(region_widgets) > len(regions):
            widgets = region_widgets.pop()
            widgets["frame"].destroy()

        # Update all widgets in place
        for idx, region in enumerate(regions):
            widgets = region_widgets[idx]
            status_canvas = widgets["status_canvas"]
            img_canvas = widgets["img_canvas"]
            name_label = widgets["name_label"]
            pause_btn = widgets["pause_btn"]
            mute_sound_btn = widgets["mute_sound_btn"]
            mute_tts_btn = widgets["mute_tts_btn"]
            remove_btn = widgets["remove_btn"]

            # Status Indicator
            status_height = 100
            status_width = 48
            if region.get("paused", False):
                status_text = paused_text_var.get()
                status_color = paused_color_var.get()
            elif region.get("alert", False):
                status_text = alert_text_var.get()
                status_color = alert_color_var.get()
            else:
                status_text = green_text_var.get()
                status_color = green_color_var.get()
            status_canvas.configure(bg=status_color)
            status_canvas.delete("all")
            img_status = create_rotated_text_image(
                status_text, status_width, status_height, color="#fff",
                bgcolor=status_color, font_size=16
            )
            status_imgtk = ImageTk.PhotoImage(img_status)
            status_canvas.create_image(
                status_width // 2,
                status_height // 2,
                anchor="center",
                image=status_imgtk
            )
            update_region_display.img_refs.append(status_imgtk)

            # Thumbnail
            thumb_width, thumb_height = 120, 100
            thumb_img = None
            if "thumbnail_path" in region and os.path.exists(region["thumbnail_path"]):
                thumb_img = Image.open(region["thumbnail_path"])
            else:
                region_coords = region.get("coords") or region.get("rect")
                if region_coords:
                    cropped = crop_region(full_img, region_coords)
                    if cropped.width > 0 and cropped.height > 0:
                        thumb_img = cropped
                    else:
                        thumb_img = Image.new("RGB", (10, 10), "#222")
                else:
                    thumb_img = Image.new("RGB", (10, 10), "#222")
            thumb_img.thumbnail((thumb_width, thumb_height), Image.LANCZOS)
            imgtk = ImageTk.PhotoImage(thumb_img)
            img_canvas.delete("all")
            img_canvas.create_image(
                (thumb_width-thumb_img.width)//2, (thumb_height-thumb_img.height)//2,
                anchor="nw", image=imgtk
            )
            img_canvas.create_rectangle(
                2, 2, thumb_width-2, thumb_height-2, outline="#888", width=2, dash=(4,2)
            )
            update_region_display.img_refs.append(imgtk)

            # Name label
            name_label.config(text=region.get("name", f"Region {idx+1}"))

            # Controls
            def toggle_pause_region(region=region):
                region["paused"] = not region.get("paused", False)
                save_config(config)
                update_region_display()
            pause_btn.config(
                text="Resume" if region.get("paused", False) else "Pause",
                command=toggle_pause_region
            )

            def toggle_mute_sound(region=region):
                region["mute_sound"] = not region.get("mute_sound", False)
                save_config(config)
                update_region_display()
            mute_sound_btn.config(
                text="Sound Mute" if not region.get("mute_sound", False) else "Sound Muted",
                command=toggle_mute_sound
            )

            def toggle_mute_tts(region=region):
                region["mute_tts"] = not region.get("mute_tts", False)
                save_config(config)
                update_region_display()
            mute_tts_btn.config(
                text="TTS Mute" if not region.get("mute_tts", False) else "TTS Muted",
                command=toggle_mute_tts
            )

            def make_remove(idx=idx):
                def _remove():
                    regions.pop(idx)
                    if idx < len(previous_screenshots):
                        previous_screenshots.pop(idx)
                    save_config(config)
                    update_region_display()
                return _remove
            remove_btn.config(command=make_remove(idx))

        regions_frame.update_idletasks()

    # --- Monitoring Loop ---
    def check_alerts():
        """
        Periodically check all monitored regions for changes and trigger alerts.
        """
        full_img = take_full_screenshot()
        now = time.time()
        alert_threshold = 0.99  # Or make this user-configurable

        for idx, region in enumerate(regions):
            if region.get("paused", False):
                continue
            region_coords = region.get("coords") or region.get("rect")
            if not region_coords:
                continue
            if idx >= len(previous_screenshots):
                previous_screenshots.append(crop_region(full_img, region_coords))
                region["alert"] = False
                region["last_alert_time"] = 0
                continue

            prev_img = previous_screenshots[idx]
            curr_img = crop_region(full_img, region_coords)

            if prev_img.size != curr_img.size or prev_img.width == 0 or prev_img.height == 0:
                previous_screenshots[idx] = curr_img
                region["alert"] = False
                region["last_alert_time"] = 0
                continue

            score = ssim(np.array(prev_img.convert("L")), np.array(curr_img.convert("L")))
            is_alert = bool(score < alert_threshold)

            play_alert = False
            if is_alert:
                last_alert = region.get("last_alert_time", 0)
                if not region.get("alert", False) or (now - last_alert > 5):
                    play_alert = True
                    region["last_alert_time"] = now
                region["alert"] = True
            else:
                if region.get("alert", False) and (now - region.get("last_alert_time", 0) >= 5):
                    region["alert"] = False
                region["last_alert_time"] = region.get("last_alert_time", 0)

            if play_alert:
                # Use region-specific sound if set, otherwise use the global/default sound from settings
                sound_file = region.get("sound_file") or timer_sound_var.get()
                region_name = region.get("name") or f"Region {idx+1}"
                tts_message = region.get("tts_message") or default_tts_var.get().format(name=region_name)
                if not region.get("mute_sound", False) and sound_file:
                    play_sound(sound_file)
                if not region.get("mute_tts", False) and tts_message:
                    speak_tts(tts_message)

            previous_screenshots[idx] = curr_img

        update_region_display()
        root.after(interval_var.get(), check_alerts)  # Use the user-configured interval

    root.after(2000, check_alerts)
    root.mainloop()

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

if __name__ == "__main__":
    main()