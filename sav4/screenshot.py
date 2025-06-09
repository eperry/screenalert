import pyautogui
from PIL import Image

def take_full_screenshot():
    try:
        return pyautogui.screenshot()
    except Exception as e:
        print(f"Screen capture failed: {e}")
        screen_width, screen_height = pyautogui.size()
        return Image.new("RGB", (screen_width, screen_height), color="#222")

def crop_region(img, region):
    left, top, width, height = region
    return img.crop((left, top, left + width, top + height))