"""
Main module for the Screen Region Monitor application.
Handles the GUI and delegates business logic to supporting modules.
"""

import os
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from typing import Any, Optional, Tuple
import tkinter.simpledialog as simpledialog

from PIL import Image, ImageTk
import numpy as np
from skimage.metrics import structural_similarity as ssim

from .config import load_config, save_config
from .timers import TimersManager, TimerItem, AddTimerDialog
from .region_selector import RegionSelector
from .sound import play_sound, speak_tts
from .screenshot import take_full_screenshot, crop_region
from sav4.utils import create_rotated_text_image, render_status_rotated, get_max_status_font_size, get_max_rotated_font_size

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
MONITOR_TAB_LABEL = "Monitor"

REGION_SHOTS_DIR = "region_shots"
os.makedirs(REGION_SHOTS_DIR, exist_ok=True)

# Define the words you want to fit
STATUS_WORDS = ["Paused", "Green", "Alert"]
STATUS_WIDTH = 64
STATUS_HEIGHT = 100
STATUS_FONT_SIZE = get_max_status_font_size(STATUS_WORDS, STATUS_WIDTH, STATUS_HEIGHT)

def main() -> None:
    """
    Main entry point for the Screen Region Monitor application.
    Sets up the GUI and event handlers.
    """
    config = load_config()
    timers_manager = TimersManager()
    # Load timers from config (paused)
    timers_data = config.get("timers", [])
    timers_manager.load_from_list(timers_data)

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
    notebook.pack(fill=tk.BOTH, expand=True)

    # Create tab frames
    merged_tab = ttk.Frame(notebook)
    regions_tab = ttk.Frame(notebook)
    timers_tab = ttk.Frame(notebook)
    settings_tab = ttk.Frame(notebook)

    # Add tabs to the notebook
    notebook.add(merged_tab, text=MONITOR_TAB_LABEL)
    notebook.add(regions_tab, text=REGIONS_TAB_LABEL)
    notebook.add(timers_tab, text=TIMERS_TAB_LABEL)
    notebook.add(settings_tab, text=SETTINGS_TAB_LABEL)

    # Ensure Monitoring tab is active at startup
    notebook.select(merged_tab)

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

    # --- Data Structures ---
    regions = config.setdefault("regions", [])
    previous_screenshots = []
    merged_widgets = []

    # --- Add Region/Timer Functions ---
    def add_region() -> None:
        """
        Add a new region to monitor.
        """
        selector = RegionSelector(root)
        region = selector.show()
        if region:
            left, top, width, height = region
            new_region = {
                "name": f"Region {len(regions) + 1}",
                "coords": (left, top, left + width, top + height),
                "paused": False,
                "alert": False,
                "mute_sound": False,
                "mute_tts": False,
                "thumbnail_path": "",
                "sound_file": "",
                "tts_message": "",
            }
            regions.append(new_region)
            save_config(config)
            update_merged_display()

    def add_timer_prompt() -> None:
        """
        Prompt the user to add a new timer.
        """
        dialog = AddTimerDialog(root)
        if dialog.result:
            name, seconds, auto_restart = dialog.result
            timers_manager.add_timer(name, int(seconds), auto_restart)
            config["timers"] = timers_manager.to_list()
            save_config(config)
            update_merged_display()

    # --- Controls at the Top of Monitor Tab ---
    controls_frame = ttk.Frame(merged_tab)
    controls_frame.pack(fill=tk.X, pady=(0, 10), anchor="n")

    def pause_all(paused: bool) -> None:
        """
        Pause or resume all regions and timers.
        If paused=True, pause all running; if paused=False, resume all paused.
        """
        for region in regions:
            region["paused"] = paused
        for timer in timers_manager.get_timers():
            # Only set running if the state is different
            if paused:
                timer.running = False
            else:
                # Resume only if not at zero
                if timer.remaining > 0:
                    timer.running = True
        save_config(config)
        update_merged_display()

    def toggle_pause_all():
        """
        Toggle pause state for all.
        If any region or timer is running, pause all.
        If all are paused, resume all.
        """
        any_running = any(not r.get("paused", False) for r in regions) or \
                      any(getattr(t, "running", False) and t.remaining > 0 for t in timers_manager.get_timers())
        if any_running:
            pause_all(paused=True)
            pause_all_btn.config(text="Resume All")
        else:
            pause_all(paused=False)
            pause_all_btn.config(text="Pause All")

    def mute_all_sound(mute: bool) -> None:
        """Mute or unmute sound for all regions and timers."""
        for region in regions:
            region["mute_sound"] = mute
        for timer in timers_manager.get_timers():
            timer.mute_sound = mute
        save_config(config)
        update_merged_display()

    def toggle_mute_all_sound():
        """Toggle mute state for all sound."""
        any_unmuted = any(not r.get("mute_sound", False) for r in regions) or \
                      any(not getattr(t, "mute_sound", False) for t in timers_manager.get_timers())
        mute_all_sound(mute=any_unmuted)
        mute_all_sound_btn.config(text="Unmute All Sound" if any_unmuted else "Mute All Sound")

    def mute_all_tts(mute: bool) -> None:
        """Mute or unmute TTS for all regions and timers."""
        for region in regions:
            region["mute_tts"] = mute
        for timer in timers_manager.get_timers():
            timer.mute_tts = mute
        save_config(config)
        update_merged_display()

    def toggle_mute_all_tts():
        """Toggle mute state for all TTS."""
        any_unmuted = any(not r.get("mute_tts", False) for r in regions) or \
                      any(not getattr(t, "mute_tts", False) for t in timers_manager.get_timers())
        mute_all_tts(mute=any_unmuted)
        mute_all_tts_btn.config(text="Unmute All TTS" if any_unmuted else "Mute All TTS")

    add_region_btn = ttk.Button(controls_frame, text="➕ Add Region", command=add_region)
    add_region_btn.pack(side=tk.LEFT, padx=5)
    add_timer_btn = ttk.Button(controls_frame, text="➕ Add Timer", command=add_timer_prompt)
    add_timer_btn.pack(side=tk.LEFT, padx=5)
    pause_all_btn = ttk.Button(controls_frame, text="Pause All", command=toggle_pause_all)
    pause_all_btn.pack(side=tk.LEFT, padx=5)
    mute_all_sound_btn = ttk.Button(controls_frame, text="Mute All Sound", command=toggle_mute_all_sound)
    mute_all_sound_btn.pack(side=tk.LEFT, padx=5)
    mute_all_tts_btn = ttk.Button(controls_frame, text="Mute All TTS", command=toggle_mute_all_tts)
    mute_all_tts_btn.pack(side=tk.LEFT, padx=5)

    # --- Merged List Frame ---
    merged_frame_outer = ttk.LabelFrame(merged_tab, text="Monitored Regions & Timers", padding=10)
    merged_frame_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    canvas = tk.Canvas(merged_frame_outer, borderwidth=0, background="#222", highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    merged_frame = ttk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=merged_frame, anchor="nw", tags="merged_window")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    def on_canvas_configure(event):
        canvas.itemconfig("merged_window", width=event.width)
    merged_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)
    merged_frame.grid_columnconfigure(0, weight=1)

    # --- update_merged_display must be defined after all above variables ---
    def update_merged_display() -> None:
        """
        Update all region and timer widgets in the merged tab.
        Ensures status column is rendered identically for both regions and timers,
        using only Canvas text (no images).
        """
        full_img = take_full_screenshot()
        update_merged_display.img_refs = []

        region_items = [{"type": "region", "data": region, "idx": idx} for idx, region in enumerate(regions)]
        timer_items = [{"type": "timer", "data": timer, "idx": idx} for idx, timer in enumerate(timers_manager.get_timers())]
        items = region_items + timer_items

        # Ensure merged_widgets matches items
        while len(merged_widgets) < len(items):
            rf = ttk.Frame(merged_frame, padding=4, relief="raised")
            rf.grid_columnconfigure(0, minsize=28, weight=0)
            rf.grid_columnconfigure(1, weight=0)
            rf.grid_columnconfigure(2, weight=1)
            rf.grid_columnconfigure(3, weight=0)
            rf.grid_columnconfigure(4, weight=0)

            status_canvas = tk.Canvas(rf, width=STATUS_WIDTH, height=STATUS_HEIGHT, highlightthickness=0, bd=0)
            status_canvas.grid(row=0, column=0, rowspan=3, sticky="nsw", padx=(0, 8), pady=0)

            img_canvas = tk.Canvas(rf, height=STATUS_HEIGHT, highlightthickness=0, bd=0, bg="#111")
            img_canvas.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=0, pady=0)

            name_label = ttk.Label(rf)
            name_label.grid(row=0, column=2, sticky="w", padx=(0, 8))

            controls_frame_row = ttk.Frame(rf)
            controls_frame_row.grid(row=0, column=3, rowspan=3, sticky="e", padx=2)
            controls_frame_row.grid_columnconfigure(0, weight=1)

            pause_btn = ttk.Button(controls_frame_row, width=10)
            pause_btn.grid(row=0, column=0, sticky="ew", pady=2)

            mute_sound_btn = ttk.Button(controls_frame_row, width=14)
            mute_sound_btn.grid(row=1, column=0, sticky="ew", pady=2)

            mute_tts_btn = ttk.Button(controls_frame_row, width=14)
            mute_tts_btn.grid(row=2, column=0, sticky="ew", pady=2)

            remove_btn = ttk.Button(rf, text="❌", width=3)
            remove_btn.grid(row=0, column=4, rowspan=3, sticky="e", padx=(8,2), pady=2)

            rf.grid(row=len(merged_widgets), column=0, sticky="ew", padx=8, pady=6)
            merged_widgets.append({
                "frame": rf,
                "status_canvas": status_canvas,
                "img_canvas": img_canvas,
                "name_label": name_label,
                "pause_btn": pause_btn,
                "mute_sound_btn": mute_sound_btn,
                "mute_tts_btn": mute_tts_btn,
                "remove_btn": remove_btn,
            })

        # Remove extra widgets if items were deleted
        while len(merged_widgets) > len(items):
            widgets = merged_widgets.pop()
            widgets["frame"].destroy()

        # Update all widgets in place
        for idx, item in enumerate(items):
            widgets = merged_widgets[idx]
            status_canvas = widgets["status_canvas"]
            img_canvas = widgets["img_canvas"]
            name_label = widgets["name_label"]
            pause_btn = widgets["pause_btn"]
            mute_sound_btn = widgets["mute_sound_btn"]
            mute_tts_btn = widgets["mute_tts_btn"]
            remove_btn = widgets["remove_btn"]

            # --- Set larger font for name label ---
            name_label.config(font=("Segoe UI", 16, "bold"))

            # --- Set name text ---
            if item["type"] == "region":
                region = item["data"]
                name_label.config(text=region.get("name", f"Region {item['idx']+1}"))
            elif item["type"] == "timer":
                timer = item["data"]
                name_label.config(text=timer.name)

            # --- Add/Edit Button (Pencil Icon) above Remove Button ---
            # Only add once per widget
            if not hasattr(widgets, "edit_btn"):
                edit_btn = ttk.Button(
                    widgets["frame"],
                    text="✏️",
                    width=3,
                    command=lambda idx=idx: edit_monitor_name(idx)
                )
                edit_btn.grid(row=0, column=4, sticky="e", padx=(8,2), pady=(2, 28))
                widgets["edit_btn"] = edit_btn
            else:
                widgets["edit_btn"].config(command=lambda idx=idx: edit_monitor_name(idx))

            # --- Status column (region or timer) ---
            if item["type"] == "region":
                region = item["data"]
                if region.get("paused", False):
                    status_text = paused_text_var.get()
                    status_color = paused_color_var.get()
                elif region.get("alert", False):
                    status_text = alert_text_var.get()
                    status_color = alert_color_var.get()
                else:
                    status_text = green_text_var.get()
                    status_color = green_color_var.get()
            elif item["type"] == "timer":
                timer = item["data"]
                if not timer.running:
                    status_text = paused_text_var.get()
                    status_color = paused_color_var.get()
                elif timer.remaining <= 0:
                    status_text = alert_text_var.get()
                    status_color = alert_color_var.get()
                else:
                    status_text = green_text_var.get()
                    status_color = green_color_var.get()

            # Draw status column using only Canvas text
            status_canvas.configure(bg=status_color)
            status_canvas.delete("all")
            # Use a font size that fits the height, minus a small margin
            font_size = get_max_rotated_font_size(status_text, STATUS_WIDTH, STATUS_HEIGHT)
            font = ("Segoe UI", font_size, "bold")
            status_canvas.create_text(
                STATUS_WIDTH // 2,
                STATUS_HEIGHT // 2,
                text=status_text,
                fill="#fff",
                font=font,
                angle=90,
                anchor="center"
            )

            # --- Region thumbnail or timer countdown ---
            if item["type"] == "region":
                # Static thumbnail for region (do not scale, always 120x100)
                thumb_width, thumb_height = 120, 100
                img_canvas.config(width=thumb_width, height=thumb_height)
                img_canvas.delete("all")
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
                imgtk = ImageTk.PhotoImage(thumb_img)
                img_canvas.create_image(
                    (thumb_width - thumb_img.width) // 2,
                    (thumb_height - thumb_img.height) // 2,
                    anchor="nw", image=imgtk
                )
                img_canvas.create_rectangle(
                    2, 2, thumb_width-2, thumb_height-2, outline="#888", width=2, dash=(4,2)
                )
                update_merged_display.img_refs.append(imgtk)

                def toggle_pause_region(region=region):
                    region["paused"] = not region.get("paused", False)
                    save_config(config)
                    update_merged_display()
                pause_btn.config(
                    text="Resume" if region.get("paused", False) else "Pause",
                    command=toggle_pause_region
                )

                def toggle_mute_sound(region=region):
                    region["mute_sound"] = not region.get("mute_sound", False)
                    save_config(config)
                    update_merged_display()
                mute_sound_btn.config(
                    text="Sound Mute" if not region.get("mute_sound", False) else "Sound Muted",
                    command=toggle_mute_sound
                )

                def toggle_mute_tts(region=region):
                    region["mute_tts"] = not region.get("mute_tts", False)
                    save_config(config)
                    update_merged_display()
                mute_tts_btn.config(
                    text="TTS Mute" if not region.get("mute_tts", False) else "TTS Muted",
                    command=toggle_mute_tts
                )

                def make_remove(idx=item["idx"]):
                    def _remove():
                        regions.pop(idx)
                        if idx < len(previous_screenshots):
                            previous_screenshots.pop(idx)
                        save_config(config)
                        update_merged_display()
                    return _remove
                remove_btn.config(command=make_remove())

            elif item["type"] == "timer":
                timer = item["data"]
                # Timer: show countdown as text in column 2, no image, width auto-scales
                img_canvas.delete("all")
                countdown_text = str(timer.remaining)
                countdown_font_size = int(100 * 0.75)
                temp_font = ("Segoe UI", countdown_font_size, "bold")
                temp_id = img_canvas.create_text(0, 0, text=countdown_text, font=temp_font, anchor="nw")
                bbox = img_canvas.bbox(temp_id)
                img_canvas.delete(temp_id)
                text_width = (bbox[2] - bbox[0]) if bbox else 60
                canvas_width = max(60, text_width + 32)
                img_canvas.config(width=canvas_width, height=100)
                img_canvas.create_rectangle(
                    2, 2, canvas_width-2, 100-2, outline="#888", width=2, dash=(4,2)
                )
                img_canvas.create_text(
                    canvas_width // 2,
                    100 // 2,
                    text=countdown_text,
                    fill="#fff",
                    font=temp_font
                )

                name_label.config(text=timer.name)

                def pause_timer(timer=timer):
                    timer.running = False
                    config["timers"] = timers_manager.to_list()
                    save_config(config)
                    update_merged_display()

                def restart_timer(timer=timer):
                    timer.remaining = timer.initial_seconds
                    timer.running = True
                    config["timers"] = timers_manager.to_list()
                    save_config(config)
                    update_merged_display()

                def toggle_mute_sound(timer=timer):
                    timer.mute_sound = not timer.mute_sound
                    config["timers"] = timers_manager.to_list()
                    save_config(config)
                    update_merged_display()

                def toggle_mute_tts(timer=timer):
                    timer.mute_tts = not timer.mute_tts
                    config["timers"] = timers_manager.to_list()
                    save_config(config)
                    update_merged_display()

                if timer.remaining <= 0:
                    pause_btn.config(
                        text="Restart",
                        command=restart_timer
                    )
                elif timer.running:
                    pause_btn.config(
                        text="Pause",
                        command=pause_timer
                    )
                else:
                    pause_btn.config(
                        text="Restart",
                        command=restart_timer
                    )

                mute_sound_btn.config(
                    text="Sound Mute" if not timer.mute_sound else "Sound Muted",
                    command=toggle_mute_sound
                )
                mute_tts_btn.config(
                    text="TTS Mute" if not timer.mute_tts else "TTS Muted",
                    command=toggle_mute_tts
                )

                def make_remove(idx=item["idx"]):
                    def _remove():
                        timers_manager.remove_timer(idx - len(region_items))
                        config["timers"] = timers_manager.to_list()
                        save_config(config)
                        update_merged_display()
                    return _remove
                remove_btn.config(command=make_remove())

        merged_frame.update_idletasks()

    # --- Add/Edit Monitor Name Function ---
    def edit_monitor_name(idx: int) -> None:
        """
        Prompt the user to edit the monitor name for a region or timer.
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
        else:
            timer_idx = idx - len(regions)
            timers = timers_manager.get_timers()
            if 0 <= timer_idx < len(timers):
                timer = timers[timer_idx]
                current_name = timer.name
                new_name = simpledialog.askstring(
                    "Edit Name", "Enter new timer name:", initialvalue=current_name
                )
                if new_name and new_name.strip():
                    timer.name = new_name.strip()
                    config["timers"] = timers_manager.to_list()
                    save_config(config)
                    update_merged_display()

    # --- Bindings for Global Hotkeys ---
    def on_ctrl_n(event):
        """
        Global hotkey: Add new region (Ctrl+N)
        """
        add_region()

    def on_ctrl_t(event):
        """
        Global hotkey: Add new timer (Ctrl+T)
        """
        add_timer_prompt()

    root.bind("<Control-n>", on_ctrl_n)
    root.bind("<Control-t>", on_ctrl_t)

    # --- Monitoring Loop ---
    def check_alerts():
        """
        Periodically check all monitored regions for changes and trigger alerts.
        """
        full_img = take_full_screenshot()
        now = time.time()
        alert_threshold = 0.99  # Or make this user-configurable
        any_change = False

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

            if play_alert or region["alert"] != is_alert:
                any_change = True

            if play_alert:
                sound_file = region.get("sound_file") or timer_sound_var.get()
                region_name = region.get("name") or f"Region {idx+1}"
                tts_message = region.get("tts_message") or default_tts_var.get().format(name=region_name)
                if not region.get("mute_sound", False) and sound_file:
                    play_sound(sound_file)
                if not region.get("mute_tts", False) and tts_message:
                    speak_tts(tts_message)

            previous_screenshots[idx] = curr_img

        if any_change:
            update_merged_display()
        root.after(interval_var.get(), check_alerts)

    def timers_tick_loop() -> None:
        """
        Periodically update timers and refresh the merged display.
        """
        changed = timers_manager.tick_all()
        if changed:
            update_merged_display()
        root.after(500, timers_tick_loop)

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

