import pyautogui                # --- CHANGED ---
from PIL import ImageChops, ImageTk, Image, ImageEnhance, ImageOps   # --- CHANGED ---
import tkinter as tk             # --- CHANGED ---
from tkinter import filedialog   # --- CHANGED ---
import winsound                 # --- CHANGED ---
import threading
import time
import json
import os
from skimage.metrics import structural_similarity as ssim
import numpy as np

CONFIG_FILE = "screenalert_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    # Defaults
    return {
        "region": None,
        "interval": 500,
        "sound_file": "c:\\Users\\Ed\\Downloads\\mixkit-classic-alarm-995.wav"
    }

def save_config(region, interval, sound_file):
    config = {
        "region": region,
        "interval": interval,
        "sound_file": sound_file
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

class RegionSelector:
    def __init__(self):
        self.root = tk.Tk()      # --- CHANGED ---
        screen_width, screen_height = pyautogui.size()   # --- CHANGED ---
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")   # --- CHANGED ---
        self.root.attributes('-alpha', 0.3)   # --- CHANGED ---
        self.root.configure(bg='black')       # --- CHANGED ---
        self.canvas = tk.Canvas(self.root, cursor="cross", bg='gray')   # --- CHANGED ---
        self.canvas.pack(fill=tk.BOTH, expand=True)   # --- CHANGED ---
        self.start_x = self.start_y = self.rect = None   # --- CHANGED ---
        self.canvas.bind("<ButtonPress-1>", self.on_press)   # --- CHANGED ---
        self.canvas.bind("<B1-Motion>", self.on_drag)        # --- CHANGED ---
        self.canvas.bind("<ButtonRelease-1>", self.on_release)   # --- CHANGED ---
        self.region = None           # --- CHANGED ---

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
        self.root.destroy()

    def select(self):
        self.root.mainloop()
        return self.region

alert_playing = False  # Global flag

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

def create_preview_window(monitor_region):
    root = tk.Tk()
    root.title("Screen Region Monitor")
    root.attributes('-topmost', True)

    # Calculate a safe position for the preview window (bottom right corner)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    region_left, region_top, region_width, region_height = monitor_region

    preview_width = region_width
    preview_height = region_height

    preview_x = screen_width - preview_width - 50
    preview_y = screen_height - preview_height - 50

    if (preview_x < region_left + region_width and preview_x + preview_width > region_left and
        preview_y < region_top + region_height and preview_y + preview_height > region_top):
        preview_x = screen_width - preview_width - 50
        preview_y = 50  # top right

    root.geometry(f"{preview_width}x{preview_height+120}+{preview_x}+{preview_y}")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    return root, frame

def take_screenshot(region):
    return pyautogui.screenshot(region=region)

# Highlight changed areas in red
def highlight_diff(img1, img2):
    # Convert to grayscale numpy arrays
    img1_gray = np.array(img1.convert("L"))
    img2_gray = np.array(img2.convert("L"))
    # Compute SSIM and diff image
    score, diff = ssim(img1_gray, img2_gray, full=True)
    diff = (diff * 255).astype("uint8")
    # Threshold the diff image
    mask = Image.fromarray((diff < 230).astype("uint8") * 255)
    # Create a red overlay
    red = Image.new("RGBA", img2.size, (255, 0, 0, 120))
    highlighted = img2.convert("RGBA").copy()
    highlighted.paste(red, (0, 0), mask)
    return highlighted, score

def main():
    # --- Load config ---
    config = load_config()
    sound_file = config.get("sound_file", "c:\\Users\\Ed\\Downloads\\mixkit-classic-alarm-995.wav")
    interval = config.get("interval", 500)

    # --- Always select region on startup ---
    monitor_region = RegionSelector().select()

    root, frame = create_preview_window(monitor_region)

    # --- UI Controls ---
    paused = False
    countdown = interval // 1000
    previous_screenshot = take_screenshot(monitor_region)
    imgtk = ImageTk.PhotoImage(previous_screenshot)

    # Region display
    region_var = tk.StringVar(value=str(monitor_region))
    region_label = tk.Label(frame, textvariable=region_var)
    region_label.pack(side=tk.TOP, fill=tk.X)

    # Sound display and selector
    sound_var = tk.StringVar(value=sound_file)
    sound_frame = tk.Frame(frame)
    sound_frame.pack(side=tk.TOP, fill=tk.X)
    tk.Label(sound_frame, text="Sound:").pack(side=tk.LEFT)
    sound_entry = tk.Entry(sound_frame, textvariable=sound_var, width=40)
    sound_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    def choose_sound():
        file = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if file:
            sound_var.set(file)
    tk.Button(sound_frame, text="Browse", command=choose_sound).pack(side=tk.LEFT)

    # Interval control
    interval_frame = tk.Frame(frame)
    interval_frame.pack(side=tk.TOP, fill=tk.X)
    tk.Label(interval_frame, text="Interval (ms):").pack(side=tk.LEFT)
    interval_var = tk.IntVar(value=interval)
    interval_spin = tk.Spinbox(interval_frame, from_=100, to=10000, increment=100, textvariable=interval_var, width=6)
    interval_spin.pack(side=tk.LEFT)
    def update_interval():
        nonlocal interval
        interval = interval_var.get()
    interval_spin.config(command=update_interval)

    # Countdown display
    countdown_var = tk.StringVar(value="Next update in: 0s")
    countdown_label = tk.Label(frame, textvariable=countdown_var)
    countdown_label.pack(side=tk.TOP, fill=tk.X)

    # Image label
    label = tk.Label(frame, image=imgtk)
    label.pack(fill=tk.BOTH, expand=True)

    # Pause/Resume button
    def toggle_pause():
        nonlocal paused, previous_screenshot, imgtk, countdown
        paused = not paused
        if paused:
            pause_button.config(text="Resume")
        else:
            pause_button.config(text="Pause")
            previous_screenshot = take_screenshot(monitor_region)
            imgtk = ImageTk.PhotoImage(previous_screenshot)
            label.config(image=imgtk)
            countdown = interval // 1000

    pause_button = tk.Button(frame, text="Pause", command=toggle_pause)
    pause_button.pack(side=tk.TOP, fill=tk.X)

    # --- Monitoring Loop ---
    def update_image():
        nonlocal previous_screenshot, imgtk, countdown
        if not paused:
            if countdown <= 0:
                current_screenshot = take_screenshot(monitor_region)
                highlighted, score = highlight_diff(previous_screenshot, current_screenshot)
                if score < 0.98:  # Lower means more different; adjust threshold as needed
                    print(f"Change detected! SSIM: {score:.3f}")
                    play_alert(sound_var.get())
                    imgtk = ImageTk.PhotoImage(highlighted)
                else:
                    imgtk = ImageTk.PhotoImage(current_screenshot)
                previous_screenshot = current_screenshot
                label.config(image=imgtk)
                countdown = interval // 1000
            else:
                countdown -= 1
        countdown_var.set(f"Next update in: {countdown}s")
        root.after(1000, update_image)

    def on_exit():
        # Save config on exit (region is saved but ignored on next start)
        save_config(
            list(monitor_region),
            interval_var.get(),
            sound_var.get()
        )
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_exit)

    update_image()
    root.mainloop()

if __name__ == "__main__":
    main()