import tkinter as tk
from tkinter import ttk
import time
import numpy as np
from PIL import ImageTk, Image
from skimage.metrics import structural_similarity as ssim
import tkinter.filedialog as fd
import tkinter.colorchooser as cc
from .timers import TimersManager
from tkinter import simpledialog, messagebox
from tkinter.simpledialog import Dialog

from .config import load_config, save_config
from .region_selector import RegionSelector
from .screenshot import take_full_screenshot, crop_region
from .sound import play_sound, speak_tts
from .utils import create_rotated_text_image

root = tk.Tk()  # Ensure root is defined before using it

def main():
    config = load_config()
    regions = config["regions"]
    interval = int(config.get("interval", 1000))
    highlight_time = int(config.get("highlight_time", 5))

    timers_manager = TimersManager()  # <-- Add this line

    root.title("Screen Region Monitor")
    root.geometry("1000x600")

    interval_var = tk.IntVar(value=interval)
    highlight_time_var = tk.IntVar(value=highlight_time)
    alert_display_time_var = tk.IntVar(value=highlight_time)
    mute_timeout_var = tk.IntVar(value=10)
    default_sound_var = tk.StringVar(value=config.get("default_sound", ""))
    default_tts_var = tk.StringVar(value=config.get("default_tts", "Alert {name}"))
    alert_threshold_var = tk.DoubleVar(value=config.get("alert_threshold", 0.99))
    green_text_var = tk.StringVar(value=config.get("green_text", "Green"))
    green_color_var = tk.StringVar(value=config.get("green_color", "#080"))
    paused_text_var = tk.StringVar(value=config.get("paused_text", "Paused"))
    paused_color_var = tk.StringVar(value=config.get("paused_color", "#08f"))
    alert_text_var = tk.StringVar(value=config.get("alert_text", "Alert"))
    alert_color_var = tk.StringVar(value=config.get("alert_color", "#a00"))

    # Notebook tabs
    notebook = ttk.Notebook(root)
    regions_tab = ttk.Frame(notebook)
    settings_tab = ttk.Frame(notebook)
    timers_tab = ttk.Frame(notebook)
    notebook.add(regions_tab, text="Regions")
    notebook.add(settings_tab, text="Settings")
    notebook.add(timers_tab, text="Timers")
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Status bar
    status = ttk.Label(root, text="Ready", anchor="w")
    status.pack(fill=tk.X, side=tk.BOTTOM)

    paused = False
    full_img = take_full_screenshot()
    previous_screenshots = [crop_region(full_img, r["rect"]) for r in regions]

    def update_pause_button_text():
        pause_button.config(text="Resume" if paused else "Pause")

    def toggle_pause():
        nonlocal paused
        paused = not paused
        update_pause_button_text()

    def add_region():
        nonlocal paused
        if paused:
            return
        paused = True
        root.withdraw()
        region = RegionSelector(root).select()
        root.deiconify()
        if region and all(region):
            region_name = f"Region {len(regions)+1}"
            regions.append({
                "rect": region,
                "name": region_name,
                "paused": False,
                "mute_sound": False,
                "mute_tts": False,
                "mute_sound_until": 0,
                "mute_tts_until": 0,
                "last_alert_time": 0
            })
            full_img = take_full_screenshot()
            previous_screenshots.append(crop_region(full_img, region))
            update_region_display()
        paused = False
        update_pause_button_text()

    region_widgets = []  # Track region widgets for reuse
    timers = []
    timer_widgets = []

    def update_region_display():
        nonlocal paused

        full_img = take_full_screenshot()
        update_region_display.img_refs = []

        # Ensure region_widgets matches regions
        while len(region_widgets) < len(regions):
            # Create new region frame and widgets
            rf = ttk.Frame(regions_frame, style="Region.TFrame", padding=4, relief="raised")
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
            name_label = ttk.Label(rf, style="Region.TLabel")
            name_label.grid(row=0, column=2, sticky="w", padx=(0, 8))

            # Controls frame
            controls_frame = ttk.Frame(rf, style="Region.TFrame")
            controls_frame.grid(row=0, column=3, rowspan=3, sticky="e", padx=2)
            controls_frame.grid_columnconfigure(0, weight=1)

            # Pause button
            pause_btn = ttk.Button(controls_frame, width=10)
            pause_btn.grid(row=0, column=0, sticky="ew", pady=2)

            # Mute sound button
            mute_sound_btn = ttk.Button(controls_frame, style="Mute.TButton", width=14)
            mute_sound_btn.grid(row=1, column=0, sticky="ew", pady=2)

            # Mute TTS button
            mute_tts_btn = ttk.Button(controls_frame, style="Mute.TButton", width=14)
            mute_tts_btn.grid(row=2, column=0, sticky="ew", pady=2)

            # Mute sound label
            mute_sound_label = ttk.Label(controls_frame, width=6)
            mute_sound_label.grid(row=1, column=2, sticky="w", padx=(4,0))

            # Mute TTS label
            mute_tts_label = ttk.Label(controls_frame, width=6)
            mute_tts_label.grid(row=2, column=2, sticky="w", padx=(4,0))

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
                "mute_sound_label": mute_sound_label,
                "mute_tts_label": mute_tts_label,
                "remove_btn": remove_btn,
            })

        # Remove extra widgets if regions were deleted
        while len(region_widgets) > len(regions):
            widgets = region_widgets.pop()
            widgets["frame"].destroy()

        # Update all widgets in place
        for idx, region in enumerate(regions):
            widgets = region_widgets[idx]
            rf = widgets["frame"]
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
            if region.get("paused", False) or paused:
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
            img_status = create_rotated_text_image(status_text, status_width, status_height, color="#fff", bgcolor=status_color, font_size=16)
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
            cropped = crop_region(full_img, region["rect"])
            if cropped.width == 0 or cropped.height == 0:
                cropped = Image.new("RGB", (10, 10), "#222")
            cropped.thumbnail((thumb_width, thumb_height), Image.LANCZOS)
            thumb_img = cropped
            imgtk = ImageTk.PhotoImage(thumb_img)
            img_canvas.delete("all")
            img_canvas.create_image((thumb_width-thumb_img.width)//2, (thumb_height-thumb_img.height)//2, anchor="nw", image=imgtk)
            img_canvas.create_rectangle(2, 2, thumb_width-2, thumb_height-2, outline="#888", width=2, dash=(4,2))
            update_region_display.img_refs.append(imgtk)

            # Name label
            name_label.config(text=region.get("name", f"Region {idx+1}"))

            # Controls
            def toggle_pause_region(region=region):
                region["paused"] = not region.get("paused", False)
                save_config(
                    regions,
                    interval_var.get(),
                    highlight_time_var.get(),
                    default_sound_var.get(),
                    default_tts_var.get()
                )
                update_region_display()
            pause_btn.config(
                text="Resume" if region.get("paused", False) else "Pause",
                command=toggle_pause_region
            )

            def toggle_mute_sound(region=region):
                mute_timeout = mute_timeout_var.get() * 60  # minutes to seconds
                if not region.get("mute_sound", False):
                    region["mute_sound"] = True
                    region["mute_sound_until"] = time.time() + mute_timeout
                else:
                    region["mute_sound"] = False
                    region["mute_sound_until"] = 0
                save_config(
                    regions,
                    interval_var.get(),
                    highlight_time_var.get(),
                    default_sound_var.get(),
                    default_tts_var.get()
                )
                update_region_display()
            mute_sound_btn.config(
                text="Sound Mute" if not region.get("mute_sound", False) else "Sound Muted",
                command=toggle_mute_sound
            )
            # Countdown label for mute sound
            mute_sound_label = widgets["mute_sound_label"]
            if region.get("mute_sound", False):
                remaining = int(max(0, region.get("mute_sound_until", 0) - time.time()))
                if remaining <= 0:
                    region["mute_sound"] = False
                    region["mute_sound_until"] = 0
                    mute_sound_label.config(text="")
                else:
                    mute_sound_label.config(text=f"{remaining}s")
            else:
                mute_sound_label.config(text="")

            # --- TTS Button and Countdown ---
            def toggle_mute_tts(region=region):
                mute_timeout = mute_timeout_var.get() * 60  # minutes to seconds
                if not region.get("mute_tts", False):
                    region["mute_tts"] = True
                    region["mute_tts_until"] = time.time() + mute_timeout
                else:
                    region["mute_tts"] = False
                    region["mute_tts_until"] = 0
                save_config(
                    regions,
                    interval_var.get(),
                    highlight_time_var.get(),
                    default_sound_var.get(),
                    default_tts_var.get()
                )
                update_region_display()
            mute_tts_btn.config(
                text="TTS Mute" if not region.get("mute_tts", False) else "TTS Muted",
                command=toggle_mute_tts
            )
            # Countdown label for mute tts
            mute_tts_label = widgets["mute_tts_label"]
            if region.get("mute_tts", False):
                remaining = int(max(0, region.get("mute_tts_until", 0) - time.time()))
                if remaining <= 0:
                    region["mute_tts"] = False
                    region["mute_tts_until"] = 0
                    mute_tts_label.config(text="")
                else:
                    mute_tts_label.config(text=f"{remaining}s")
            else:
                mute_tts_label.config(text="")

            def make_remove(idx=idx):
                def _remove():
                    regions.pop(idx)
                    previous_screenshots.pop(idx)
                    update_region_display()
                return _remove
            remove_btn.config(command=make_remove(idx))

        regions_frame.update_idletasks()

    # --- Controls ---
    controls = ttk.LabelFrame(regions_tab, text="Controls", padding=10)
    controls.pack(fill=tk.X, pady=(0, 10))
    add_btn = ttk.Button(controls, text="➕ Add Region", command=add_region)
    add_btn.pack(side=tk.LEFT, padx=5)
    pause_button = ttk.Button(controls, text="Pause", command=toggle_pause)
    pause_button.pack(side=tk.LEFT, padx=5)
    add_timer_btn = ttk.Button(controls, text="➕ Add Timer", command=lambda: open_add_timer_window())
    add_timer_btn.pack(side=tk.LEFT, padx=5)

    # --- Monitored Regions Section ---
    regions_frame_outer = ttk.LabelFrame(regions_tab, text="Monitored Regions", padding=10)
    regions_frame_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    canvas = tk.Canvas(regions_frame_outer, borderwidth=0, background="#222", highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    regions_frame = ttk.Frame(canvas, style="Region.TFrame")
    canvas_window = canvas.create_window((0, 0), window=regions_frame, anchor="nw", tags="regions_window")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    def on_canvas_configure(event):
        canvas.itemconfig("regions_window", width=event.width)
    regions_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)
    regions_frame.grid_columnconfigure(0, weight=1)

    # --- Settings Section ---
    settings_frame = ttk.LabelFrame(settings_tab, text="Settings", padding=10)
    settings_frame.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(settings_frame, text="Interval (ms):").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    interval_spin = ttk.Spinbox(settings_frame, from_=100, to=10000, increment=100, textvariable=interval_var, width=7)
    interval_spin.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    ttk.Label(settings_frame, text="Alert Display Time (s):").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    alert_display_spin = ttk.Spinbox(settings_frame, from_=1, to=60, increment=1, textvariable=alert_display_time_var, width=7)
    alert_display_spin.grid(row=1, column=1, sticky="w", padx=5, pady=2)
    alert_display_spin.bind("<FocusOut>", lambda e: save_settings())
    ttk.Label(settings_frame, text="Mute Timeout (min):").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    mute_timeout_spin = ttk.Spinbox(settings_frame, from_=1, to=60, increment=1, textvariable=mute_timeout_var, width=5)
    mute_timeout_spin.grid(row=2, column=1, sticky="w", padx=5, pady=2)

    def browse_default_sound():
        file = fd.askopenfilename(title="Select Sound File", filetypes=[("Audio Files", "*.wav *.mp3 *.ogg"), ("All Files", "*.*")])
        if file:
            default_sound_var.set(file)
            save_settings()

    ttk.Label(settings_frame, text="Default Alert Sound:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
    default_sound_entry = ttk.Entry(settings_frame, textvariable=default_sound_var, width=25)
    default_sound_entry.grid(row=3, column=1, sticky="w", padx=5, pady=2)
    default_sound_entry.bind("<FocusOut>", lambda e: save_settings())
    browse_default_btn = ttk.Button(settings_frame, text="Browse...", command=browse_default_sound)
    browse_default_btn.grid(row=3, column=2, sticky="w", padx=2, pady=2)
    ttk.Label(settings_frame, text="Default TTS:").grid(row=4, column=0, sticky="e", padx=5, pady=2)
    default_tts_entry = ttk.Entry(settings_frame, textvariable=default_tts_var, width=20)
    default_tts_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)
    default_tts_entry.bind("<FocusOut>", lambda e: save_settings())
    ttk.Label(settings_frame, text="Alert Threshold (0-1):").grid(row=5, column=0, sticky="e", padx=5, pady=2)
    threshold_spin = ttk.Spinbox(settings_frame, from_=0.80, to=1.00, increment=0.01, textvariable=alert_threshold_var, width=7, format="%.2f")
    threshold_spin.grid(row=5, column=1, sticky="w", padx=5, pady=2)
    threshold_spin.bind("<FocusOut>", lambda e: save_settings())

    # Green State
    ttk.Label(settings_frame, text="Normal Text:").grid(row=6, column=0, sticky="e", padx=5, pady=2)
    green_text_entry = ttk.Entry(settings_frame, textvariable=green_text_var, width=12)
    green_text_entry.grid(row=6, column=1, sticky="w", padx=2, pady=2)
    green_text_entry.bind("<FocusOut>", lambda e: save_settings())
    green_color_btn = ttk.Button(settings_frame, text="Color...", width=8)
    green_color_btn.grid(row=6, column=2, sticky="w", padx=2, pady=2)
    def choose_green_color():
        color = cc.askcolor(color=green_color_var.get())[1]
        if color:
            green_color_var.set(color)
            save_settings()
    green_color_btn.config(command=choose_green_color)

    # Paused State
    ttk.Label(settings_frame, text="Paused Text:").grid(row=7, column=0, sticky="e", padx=5, pady=2)
    paused_text_entry = ttk.Entry(settings_frame, textvariable=paused_text_var, width=12)
    paused_text_entry.grid(row=7, column=1, sticky="w", padx=2, pady=2)
    paused_text_entry.bind("<FocusOut>", lambda e: save_settings())
    paused_color_btn = ttk.Button(settings_frame, text="Color...", width=8)
    paused_color_btn.grid(row=7, column=2, sticky="w", padx=2, pady=2)
    def choose_paused_color():
        color = cc.askcolor(color=paused_color_var.get())[1]
        if color:
            paused_color_var.set(color)
            save_settings()
    paused_color_btn.config(command=choose_paused_color)

    # Alert State
    ttk.Label(settings_frame, text="Alert Text:").grid(row=8, column=0, sticky="e", padx=5, pady=2)
    alert_text_entry = ttk.Entry(settings_frame, textvariable=alert_text_var, width=12)
    alert_text_entry.grid(row=8, column=1, sticky="w", padx=2, pady=2)
    alert_text_entry.bind("<FocusOut>", lambda e: save_settings())
    alert_color_btn = ttk.Button(settings_frame, text="Color...", width=8)
    alert_color_btn.grid(row=8, column=2, sticky="w", padx=2, pady=2)
    def choose_alert_color():
        color = cc.askcolor(color=alert_color_var.get())[1]
        if color:
            alert_color_var.set(color)
            save_settings()
    alert_color_btn.config(command=choose_alert_color)

    timer_sound_var = tk.StringVar(value=config.get("timer_sound", ""))

    # --- Timers Tab ---
    timers_frame = ttk.Frame(timers_tab)
    timers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Add Pause, Auto-Restart, Mute Sound, Mute TTS, Remove columns
    timers_tree = ttk.Treeview(
        timers_frame,
        columns=("name", "remaining", "pause", "auto_restart", "mute_sound", "mute_tts", "remove"),
        show="headings",
        height=10
    )
    timers_tree.heading("name", text="Timer Name")
    timers_tree.heading("remaining", text="Time Left (s)")
    timers_tree.heading("pause", text="Pause")
    timers_tree.heading("auto_restart", text="Auto-Restart")
    timers_tree.heading("mute_sound", text="Mute Sound")
    timers_tree.heading("mute_tts", text="Mute TTS")
    timers_tree.heading("remove", text="")
    timers_tree.column("pause", width=60, anchor="center", stretch=False)
    timers_tree.column("auto_restart", width=90, anchor="center", stretch=False)
    timers_tree.column("mute_sound", width=80, anchor="center", stretch=False)
    timers_tree.column("mute_tts", width=80, anchor="center", stretch=False)
    timers_tree.column("remove", width=40, anchor="center", stretch=False)
    timers_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    def refresh_timers_tree():
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
            percent_left = timer.remaining / timer.total_seconds if timer.total_seconds else 0
            if percent_left <= alert_threshold:
                row_color = alert_color
            elif percent_left <= warning_threshold:
                row_color = warning_color
            else:
                row_color = ""
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
            if row_color:
                timers_tree.tag_configure(f"timer_row_{idx}", background=row_color)
            else:
                timers_tree.tag_configure(f"timer_row_{idx}", background="")

    def on_timer_tree_click(event):
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

    from tkinter import messagebox

    def timer_finished(timer):
        # ...existing code...
        
            warning_threshold_var = tk.DoubleVar(value=config.get("timer_warning_threshold", 0.10))
            warning_color_var = tk.StringVar(value=config.get("timer_warning_color", "#FFD700"))  # yellow
            alert_threshold_var = tk.DoubleVar(value=config.get("timer_alert_threshold", 0.01))
            alert_color_var = tk.StringVar(value=config.get("timer_alert_color", "#FF3333"))  # red

            # --- Settings Section ---
            # ...existing settings controls...
        
            ttk.Label(settings_frame, text="Timer Warning Threshold (%):").grid(row=9, column=0, sticky="e", padx=5, pady=2)
            warning_threshold_spin = ttk.Spinbox(settings_frame, from_=1, to=99, increment=1, textvariable=warning_threshold_var, width=7)
            warning_threshold_spin.grid(row=9, column=1, sticky="w", padx=5, pady=2)
            warning_threshold_spin.bind("<FocusOut>", lambda e: save_settings())
            warning_color_btn = ttk.Button(settings_frame, text="Color...", width=8)
            warning_color_btn.grid(row=9, column=2, sticky="w", padx=2, pady=2)
            def choose_warning_color():
                color = cc.askcolor(color=warning_color_var.get())[1]
                if color:
                    warning_color_var.set(color)
                    save_settings()
            warning_color_btn.config(command=choose_warning_color)
        
            ttk.Label(settings_frame, text="Timer Alert Threshold (%):").grid(row=10, column=0, sticky="e", padx=5, pady=2)
            alert_threshold_spin = ttk.Spinbox(settings_frame, from_=0.1, to=10, increment=0.1, textvariable=alert_threshold_var, width=7, format="%.2f")
            alert_threshold_spin.grid(row=10, column=1, sticky="w", padx=5, pady=2)
            alert_threshold_spin.bind("<FocusOut>", lambda e: save_settings())
            alert_color_btn2 = ttk.Button(settings_frame, text="Color...", width=8)
            alert_color_btn2.grid(row=10, column=2, sticky="w", padx=2, pady=2)
            def choose_alert_color2():
                color = cc.askcolor(color=alert_color_var.get())[1]
                if color:
                    alert_color_var.set(color)
                    save_settings()
            alert_color_btn2.config(command=choose_alert_color2)
        
            # Update save_settings to include new settings
            def save_settings():
                config["interval"] = interval_var.get()
                config["highlight_time"] = highlight_time_var.get()
                config["default_sound"] = default_sound_var.get()
                config["default_tts"] = default_tts_var.get()
                config["alert_threshold"] = alert_threshold_var.get()
                config["green_text"] = green_text_var.get()
                config["green_color"] = green_color_var.get()
                config["paused_text"] = paused_text_var.get()
                config["paused_color"] = paused_color_var.get()
                config["alert_text"] = alert_text_var.get()
                config["alert_color"] = alert_color_var.get()
                config["timer_warning_threshold"] = warning_threshold_var.get()
                config["timer_warning_color"] = warning_color_var.get()
                config["timer_alert_threshold"] = alert_threshold_var.get()
                config["timer_alert_color"] = alert_color_var.get()
                save_config(config)
        
        # ...existing code...        # No popup
        # Play sound if not muted
        if not timer.mute_sound and timer_sound_var.get():
            play_sound(timer_sound_var.get())
        # Speak TTS if not muted
        if not timer.mute_tts:
            speak_tts(f"{timer.name} has finished")

    # Assign the finish callback to all timers
    def assign_finish_callbacks():
        for timer in timers_manager.get_timers():
            timer.on_finish = timer_finished

    class AddTimerDialog(Dialog):
        def body(self, master):
            tk.Label(master, text="Timer Name:").grid(row=0, column=0, sticky="e")
            tk.Label(master, text="Time (seconds):").grid(row=1, column=0, sticky="e")
            self.name_var = tk.StringVar()
            self.seconds_var = tk.StringVar()
            self.auto_restart_var = tk.BooleanVar()
            self.name_entry = tk.Entry(master, textvariable=self.name_var)
            self.seconds_entry = tk.Entry(master, textvariable=self.seconds_var)
            self.auto_restart_cb = tk.Checkbutton(master, text="Auto-Restart", variable=self.auto_restart_var)
            self.name_entry.grid(row=0, column=1, padx=5, pady=5)
            self.seconds_entry.grid(row=1, column=1, padx=5, pady=5)
            self.auto_restart_cb.grid(row=2, column=1, sticky="w", padx=5, pady=5)
            return self.name_entry  # initial focus

        def apply(self):
            self.result = (self.name_var.get(), self.seconds_var.get(), self.auto_restart_var.get())

    def add_timer_prompt():
        dialog = AddTimerDialog(timers_tab, title="Add Timer")
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

    add_timer_btn = ttk.Button(timers_frame, text="Add Timer", command=add_timer_prompt)
    add_timer_btn.pack(fill=tk.X, padx=5, pady=5, side=tk.RIGHT)

    def timers_tick_loop():
        timers_manager.tick_all()
        assign_finish_callbacks()
        refresh_timers_tree()
        timers_frame.after(1000, timers_tick_loop)

    timers_tick_loop()

    root.mainloop()

if __name__ == "__main__":
    main()