import tkinter as tk
import pyautogui

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