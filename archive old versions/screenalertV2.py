import pyautogui
from PIL import ImageTk, Image
import tkinter as tk
from tkinter import filedialog
import winsound
import threading
import json
import os
from skimage.metrics import structural_similarity as ssim
import numpy as np
import time
import tkinter.ttk as ttk
import pyttsx3
import queue

CONFIG_FILE = "screenalert_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Convert old tuple regions to dicts if needed
            new_regions = []
            for r in config.get("regions", []):
                if isinstance(r, dict):
                    new_regions.append(r)
                else:
                    new_regions.append({"rect": r, "sound_file": config.get("sound_file", "c:\\Users\\Ed\\Downloads\\mixkit-classic-alarm-995.wav")})
            config["regions"] = new_regions
            if "highlight_time" not in config:
                config["highlight_time"] = 10
            return config
    return {
        "regions": [],
        "interval": 1000,
        "sound_file": "c:\\Users\\Ed\\Downloads\\mixkit-classic-alarm-995.wav",
        "highlight_time": 10
    }

def save_config(regions, interval, sound_file, highlight_time):
    config = {
        "regions": regions,
        "interval": interval,
        "sound_file": sound_file,
        "highlight_time": highlight_time
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

class RegionSelector:
    def __init__(self, master):
        self.region = None
        self.top = tk.Toplevel(master)
        self.top.attributes('-alpha', 0.3)
        self.top.configure(bg='black')
        screen_width, screen_height = pyautogui.size()
        self.top.geometry(f"{screen_width}x{screen_height}+0+0")
        self.top.overrideredirect(True)
        self.top.lift()
        self.top.focus_force()
        self.canvas = tk.Canvas(self.top, cursor="cross", bg='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.start_x = self.start_y = self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2
        )

    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        x1, y1 = int(self.start_x), int(self.start_y)
        x2, y2 = int(end_x), int(end_y)
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        self.region = (left, top, width, height)
        self.top.destroy()

    def select(self):
        self.top.grab_set()
        self.top.wait_window()
        return self.region

alert_playing = False

def play_alert(sound_file):
    global alert_playing
    if alert_playing:
        return
    alert_playing = True
    def _play():
        try:
            winsound.PlaySound(sound_file, winsound.SND_FILENAME)
        except Exception as e:
            print(f"Error playing sound: {e}")
        finally:
            global alert_playing
            alert_playing = False
    threading.Thread(target=_play, daemon=True).start()

tts_queue = queue.Queue()
tts_busy = threading.Event()

def tts_worker():
    engine = pyttsx3.init()
    while True:
        msg = tts_queue.get()
        if msg is None:
            break
        if tts_busy.is_set():
            continue  # Skip if already speaking
        tts_busy.set()
        try:
            engine.say(msg)
            engine.runAndWait()
        finally:
            tts_busy.clear()

def play_tts(message):
    if not tts_busy.is_set():
        tts_queue.put(message)

def take_full_screenshot():
    try:
        return pyautogui.screenshot()
    except Exception as e:
        print(f"Screen capture failed: {e}")
        # Return a blank image or None
        screen_width, screen_height = pyautogui.size()
        return Image.new("RGB", (screen_width, screen_height), color="#222")

def crop_region(img, region):
    left, top, width, height = region
    return img.crop((left, top, left + width, top + height))

def highlight_diff(img1, img2):
    img1_gray = np.array(img1.convert("L"))
    img2_gray = np.array(img2.convert("L"))
    score, diff = ssim(img1_gray, img2_gray, full=True)
    diff = (diff * 255).astype("uint8")
    mask = Image.fromarray((diff < 230).astype("uint8") * 255)
    red = Image.new("RGBA", img2.size, (255, 0, 0, 120))
    highlighted = img2.convert("RGBA").copy()
    highlighted.paste(red, (0, 0), mask)
    return highlighted, score

def main():
    config = load_config()
    sound_file = config.get("sound_file", "c:\\Users\\Ed\\Downloads\\mixkit-classic-alarm-995.wav")
    interval = int(config.get("interval", 1000))
    regions = config.get("regions", [])
    highlight_time = config.get("highlight_time", 10)

    root = tk.Tk()
    root.title("Screen Region Monitor")
    root.geometry("1050x400")  # 400px height to show 2 regions comfortably
    root.attributes('-topmost', True)
    root.configure(bg="#222")

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure("TFrame", background="#222")
    style.configure("TLabel", background="#222", foreground="#fff", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10, "bold"))
    style.configure("Region.TFrame", background="#333")
    style.configure("Alert.TFrame", background="#a00")
    style.configure("Region.TLabel", background="#333", foreground="#fff")
    style.configure("Alert.TLabel", background="#a00", foreground="#fff")

    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # --- Add a Notebook (tabbed interface) ---
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    # --- Tab 1: Regions ---
    regions_tab = ttk.Frame(notebook)
    notebook.add(regions_tab, text="Regions")

    # --- Tab 2: Settings ---
    settings_tab = ttk.Frame(notebook)
    notebook.add(settings_tab, text="Settings")

    paused = False
    previous_screenshots = []
    timer_interval = 200  # ms
    region_frames = []
    changed_regions = {}
    region_widgets = []

    def add_region():
        nonlocal regions, paused
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
                "sound_file": sound_var.get(),
                "sound_enabled": True,
                "tts_enabled": False,
                "tts_message": f"Alert for {region_name}"
            })
            previous_screenshots.clear()
        paused = False

    def toggle_pause():
        nonlocal paused
        paused = not paused
        pause_button.config(text="Resume" if paused else "Pause")

    # --- Controls at the top of the Regions tab ---
    controls = ttk.LabelFrame(regions_tab, text="Controls", padding=10)
    controls.pack(fill=tk.X, pady=(0, 10))

    add_btn = ttk.Button(controls, text="➕ Add Region", command=add_region)
    add_btn.pack(side=tk.LEFT, padx=5)
    pause_button = ttk.Button(controls, text="Pause", command=toggle_pause)
    pause_button.pack(side=tk.LEFT, padx=5)

    # --- Monitored Regions (scrollable) ---
    regions_frame_outer = ttk.LabelFrame(regions_tab, text="Monitored Regions", padding=10)
    regions_frame_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    canvas = tk.Canvas(regions_frame_outer, borderwidth=0, background="#222", highlightthickness=0)
    scrollbar = ttk.Scrollbar(regions_frame_outer, orient="vertical", command=canvas.yview)
    regions_frame = ttk.Frame(canvas, padding=0)

    regions_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=regions_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Settings Tab ---
    sound_frame = ttk.LabelFrame(settings_tab, text="Alert Sound", padding=10)
    sound_frame.pack(fill=tk.X, pady=(0, 10))
    sound_var = tk.StringVar(value=sound_file)
    ttk.Label(sound_frame, text="Sound:").pack(side=tk.LEFT)
    sound_entry = ttk.Entry(sound_frame, textvariable=sound_var, width=35)
    sound_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    def choose_sound():
        file = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if file:
            sound_var.set(file)
    ttk.Button(sound_frame, text="Browse", command=choose_sound).pack(side=tk.LEFT, padx=5)

    settings_frame = ttk.LabelFrame(settings_tab, text="Settings", padding=10)
    settings_frame.pack(fill=tk.X, pady=(0, 10))
    interval_var = tk.IntVar(value=interval)
    ttk.Label(settings_frame, text="Interval (ms):").pack(side=tk.LEFT)
    interval_spin = ttk.Spinbox(settings_frame, from_=100, to=10000, increment=100, textvariable=interval_var, width=7)
    interval_spin.pack(side=tk.LEFT, padx=5)
    def update_interval():
        nonlocal interval
        interval = int(interval_var.get())
    interval_spin.config(command=update_interval)
    highlight_time_var = tk.IntVar(value=highlight_time)
    ttk.Label(settings_frame, text="Highlight (s):").pack(side=tk.LEFT, padx=(10,0))
    highlight_spin = ttk.Spinbox(settings_frame, from_=1, to=60, increment=1, textvariable=highlight_time_var, width=7)
    highlight_spin.pack(side=tk.LEFT, padx=5)
    def update_highlight_time():
        nonlocal highlight_time
        highlight_time = int(highlight_time_var.get())
    highlight_spin.config(command=update_highlight_time)

    reactivate_minutes_var = tk.IntVar(value=5)  # Default: 5 minutes
    ttk.Label(settings_frame, text="Reactivate toggles after (min):").pack(side=tk.LEFT, padx=(10,0))
    reactivate_spin = ttk.Spinbox(settings_frame, from_=1, to=120, increment=1, textvariable=reactivate_minutes_var, width=5)
    reactivate_spin.pack(side=tk.LEFT, padx=5)

    def update_region_display(full_img=None):
        for rf in region_frames:
            rf.destroy()
        region_frames.clear()
        if not hasattr(update_region_display, "img_refs"):
            update_region_display.img_refs = []
        update_region_display.img_refs.clear()
        if full_img is None:
            full_img = take_full_screenshot()
        # Only create widgets if they don't exist
        while len(region_widgets) < len(regions):
            idx = len(region_widgets)
            is_alert = idx in changed_regions
            frame_style = "Alert.TFrame" if is_alert else "Region.TFrame"
            label_style = "Alert.TLabel" if is_alert else "Region.TLabel"
            # --- Fancy region frame with border and rounded corners ---
            style_to_use = frame_style if is_alert else "TFrame"
            label_style_to_use = label_style if is_alert else "TLabel"

            rf = ttk.Frame(
                regions_frame,
                style=frame_style,
                padding=4,
                relief="raised"
            )
            rf.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6, anchor="n")
            # 1. Image (rounded border effect)
            cropped = crop_region(full_img, regions[idx]["rect"])
            imgtk = ImageTk.PhotoImage(cropped.resize((200, 100)))
            img_canvas = tk.Canvas(rf, width=200, height=100, highlightthickness=0, bd=0, bg="#111")
            img_canvas.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=0, pady=0)
            img_canvas.create_image(0, 0, anchor="nw", image=imgtk)
            img_canvas.create_rectangle(2, 2, 198, 98, outline="#888", width=2, dash=(4,2))
            update_region_display.img_refs.append(imgtk)
            # 2. Region Name (with icon)
            region_name_var = tk.StringVar(value=regions[idx].get("name", f"Region {idx+1}"))
            name_frame = ttk.Frame(rf, style=frame_style)
            name_frame.grid(row=0, column=1, rowspan=1, sticky="nsew", padx=4, pady=(8,2))
            ttk.Label(name_frame, text="🖼️", font=("Segoe UI Emoji", 12)).pack(side=tk.LEFT)
            region_name_entry = ttk.Entry(name_frame, textvariable=region_name_var, width=16, style=label_style)
            region_name_entry.pack(side=tk.LEFT, padx=(4,0))
            def update_region_name(*args, i=idx, var=region_name_var):
                regions[i]["name"] = var.get()
            region_name_var.trace_add("write", update_region_name)
            # 3. Controls (sound file and tts message, with icons)
            controls_frame = ttk.Frame(rf, style=frame_style)
            controls_frame.grid(row=0, column=2, rowspan=3, sticky="nsew", padx=4, pady=0)
            # --- Sound and TTS toggle icon buttons (single row, icons change on toggle) ---

            # Remove the toggle_row and its two icon buttons at the top.

            # --- Sound file row with toggle icon ---
            sound_row = ttk.Frame(controls_frame, style=frame_style)
            sound_row.pack(side=tk.TOP, anchor="w", fill=tk.X, pady=(4,2))

            sound_enabled_var = tk.BooleanVar(value=regions[idx].get("sound_enabled", True))
            def update_sound_icon(*args, btn=None, var=None):
                btn.config(text="🔊" if var.get() else "🔈")
            sound_btn = ttk.Button(
                sound_row,
                text="🔊" if sound_enabled_var.get() else "🔈",
                width=2,
                command=lambda var=sound_enabled_var, i=idx: var.set(not var.get())
            )
            sound_btn.pack(side=tk.LEFT)
            sound_enabled_var.trace_add("write", lambda *a, btn=sound_btn, var=sound_enabled_var: update_sound_icon(btn=btn, var=var))
            def update_sound_enabled(*args, i=idx, var=sound_enabled_var):
                regions[i]["sound_enabled"] = var.get()
                if not var.get():
                    # Schedule reactivation
                    minutes = reactivate_minutes_var.get()
                    def reactivate():
                        if not regions[i]["sound_enabled"]:
                            var.set(True)
                    rf.after(minutes * 60 * 1000, reactivate)
            sound_enabled_var.trace_add("write", lambda *a, i=idx, var=sound_enabled_var: update_sound_enabled(i=i, var=var))

            region_sound_full = regions[idx].get("sound_file", sound_var.get())
            region_sound_var = tk.StringVar(value=os.path.basename(region_sound_full))
            sound_entry = ttk.Entry(sound_row, textvariable=region_sound_var, width=20)
            sound_entry.pack(side=tk.LEFT, anchor="w", padx=(2,2))
            def choose_region_sound(i=idx, var=region_sound_var):
                file = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
                if file:
                    var.set(os.path.basename(file))
                    regions[i]["sound_file"] = file
            ttk.Button(sound_row, text="...", width=2, command=choose_region_sound).pack(side=tk.LEFT, anchor="w")
            def update_region_sound_var(*args, i=idx, var=region_sound_var):
                pass
            region_sound_var.trace_add("write", update_region_sound_var)

            # --- TTS message row with toggle icon ---
            msg_row = ttk.Frame(controls_frame, style=frame_style)
            msg_row.pack(side=tk.TOP, anchor="w", fill=tk.X, pady=(2,0))

            tts_var = tk.BooleanVar(value=regions[idx].get("tts_enabled", False))
            def update_tts_icon(*args, btn=None, var=None):
                btn.config(text="🗣️" if var.get() else "🤐")
            tts_btn = ttk.Button(
                msg_row,
                text="🗣️" if tts_var.get() else "🤐",
                width=2,
                command=lambda var=tts_var, i=idx: var.set(not var.get())
            )
            tts_btn.pack(side=tk.LEFT)
            tts_var.trace_add("write", lambda *a, btn=tts_btn, var=tts_var: update_tts_icon(btn=btn, var=var))
            def update_tts_toggle(*args, i=idx, var=tts_var):
                regions[i]["tts_enabled"] = var.get()
                if not var.get():
                    # Schedule reactivation
                    minutes = reactivate_minutes_var.get()
                    def reactivate():
                        if not regions[i]["tts_enabled"]:
                            var.set(True)
                    rf.after(minutes * 60 * 1000, reactivate)
            tts_var.trace_add("write", lambda *a, i=idx, var=tts_var: update_tts_toggle(i=i, var=var))

            tts_msg_var = tk.StringVar(value=regions[idx].get("tts_message", f"Alert for region {idx+1}"))
            tts_entry = ttk.Entry(msg_row, textvariable=tts_msg_var, width=20, style=label_style)
            tts_entry.pack(side=tk.LEFT, anchor="w", padx=(2,0))
            def update_tts_msg(*args, i=idx, var=tts_msg_var):
                regions[i]["tts_message"] = var.get()
            tts_msg_var.trace_add("write", update_tts_msg)
            # 5. Remove button (X, last column, vertically centered)
            rm_btn = ttk.Button(rf, text="✖", width=2, command=lambda i=idx: remove_region(i))
            rm_btn.grid(row=0, column=3, sticky="n", padx=4, pady=(0,2))
            rm_btn.bind("<Enter>", lambda e, btn=rm_btn: btn.configure(style="Alert.TButton"))
            rm_btn.bind("<Leave>", lambda e, btn=rm_btn: btn.configure(style="TButton"))

            # Pause button (⏸️), below the X
            def toggle_region_pause(i=idx):
                regions[i]["paused"] = not regions[i].get("paused", False)
                update_region_display()

            pause_btn = ttk.Button(
                rf,
                text="⏸️" if not regions[idx].get("paused", False) else "▶️",
                width=2,
                command=toggle_region_pause
            )
            pause_btn.grid(row=1, column=3, sticky="n", padx=4, pady=(2,0))
            pause_btn_tip = ttk.Label(rf, text="Pause", font=("Segoe UI", 7), foreground="#aaa", background="#222")
            pause_btn_tip.grid(row=2, column=3, sticky="n", padx=4, pady=(0,0))

            # Add a 'paused' flag to each region if not present
            if "paused" not in regions[idx]:
                regions[idx]["paused"] = False

            # --- Adjust column configs if needed ---
            rf.grid_columnconfigure(0, minsize=200, weight=0)  # Image column wider
            rf.grid_columnconfigure(3, minsize=34, weight=0)   # Remove/Pause
            region_widgets.append({
                "frame": rf,
                "img_canvas": img_canvas,
                "region_name_var": region_name_var,
                "region_name_entry": region_name_entry,  # <-- Add this
                "sound_enabled_var": sound_enabled_var,
                "tts_var": tts_var,
                "region_sound_var": region_sound_var,
                "tts_msg_var": tts_msg_var,
                "tts_entry": tts_entry,                  # <-- Add this
                "rm_btn": rm_btn,
            })
        # Update existing widgets
        for idx, region in enumerate(regions):
            is_alert = idx in changed_regions
            frame_style = "Alert.TFrame" if is_alert else "Region.TFrame"
            label_style = "Alert.TLabel" if is_alert else "Region.TLabel"
            widgets = region_widgets[idx]
            # Update image
            cropped = crop_region(full_img, region["rect"])
            imgtk = ImageTk.PhotoImage(cropped.resize((200, 100)))
            widgets["img_canvas"].delete("all")
            widgets["img_canvas"].create_image(0, 0, anchor="nw", image=imgtk)
            widgets["img_canvas"].create_rectangle(2, 2, 198, 98, outline="#888", width=2, dash=(4,2))
            widgets["img_canvas"].image = imgtk
            update_region_display.img_refs.append(imgtk)
            # Update highlight style
            widgets["frame"].configure(style=frame_style)
            widgets["img_canvas"].configure(bg="#a00" if is_alert else "#111")
            # Update name, toggles, sound, tts
            widgets["region_name_var"].set(region.get("name", f"Region {idx+1}"))
            widgets["sound_enabled_var"].set(region.get("sound_enabled", True))
            widgets["tts_var"].set(region.get("tts_enabled", False))
            widgets["region_sound_var"].set(os.path.basename(region.get("sound_file", sound_var.get())))
            widgets["tts_msg_var"].set(region.get("tts_message", f"Alert for region {idx+1}"))
            # Also update styles for all inner frames/entries if needed:
            widgets["region_name_entry"].configure(style=label_style)
            widgets["tts_entry"].configure(style=label_style)
        # If regions were removed, destroy extra widgets
        while len(region_widgets) > len(regions):
            widgets = region_widgets.pop()
            widgets["frame"].destroy()
        root.update_idletasks()
        canvas.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def remove_region(idx):
        nonlocal regions, previous_screenshots, changed_regions
        if 0 <= idx < len(regions):
            del regions[idx]
            if idx in changed_regions:
                del changed_regions[idx]
            if previous_screenshots and idx < len(previous_screenshots):
                del previous_screenshots[idx]
            update_region_display(take_full_screenshot())
            root.update_idletasks()

    def monitor_loop():
        nonlocal previous_screenshots, interval, paused, regions, changed_regions
        while True:
            if not paused and regions:
                now = int(time.time() * 1000)
                expired = [idx for idx, t in changed_regions.items() if now - t > highlight_time_var.get() * 1000]
                for idx in expired:
                    del changed_regions[idx]
                full_screenshot = take_full_screenshot()
                if not previous_screenshots or len(previous_screenshots) != len(regions):
                    previous_screenshots = [crop_region(full_screenshot, r["rect"]) for r in regions]
                for idx, region in enumerate(regions):
                    if region.get("paused", False):
                        continue  # Skip alerting for paused regions
                    current = crop_region(full_screenshot, region["rect"])
                    highlighted, score = highlight_diff(previous_screenshots[idx], current)
                    if score < 0.98:
                        if region.get("sound_enabled", True):
                            play_alert(region.get("sound_file", sound_var.get()))
                        if region.get("tts_enabled", False):
                            play_tts(region.get("tts_message", f"Alert for {region.get('name', f'Region {idx+1}')}"))
                        changed_regions[idx] = int(time.time() * 1000)
                    previous_screenshots[idx] = current
                root.after(0, lambda img=full_screenshot: update_region_display(img))
                interval = int(interval_var.get())
            time.sleep(timer_interval / 1000.0)

    def on_exit():
        save_config(
            list(regions),
            interval_var.get(),
            sound_var.get(),
            highlight_time_var.get()
        )
        tts_queue.put(None)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_exit)
    threading.Thread(target=monitor_loop, daemon=True).start()
    threading.Thread(target=tts_worker, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()