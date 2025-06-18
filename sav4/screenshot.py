"""
Screenshot utility module for Screen Region Monitor.

Provides functions to capture screenshots of the entire screen or specific regions.
"""

from typing import Tuple, Optional
import os
import pyautogui

try:
    from PIL import ImageGrab, Image
except ImportError:
    ImageGrab = None
    Image = None

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

def capture_screen(output_path: str) -> bool:
    """
    Capture the entire screen and save it to the specified path.

    Args:
        output_path: The file path where the screenshot will be saved.

    Returns:
        True if the screenshot was saved successfully, False otherwise.
    """
    if ImageGrab is None:
        return False
    try:
        img = ImageGrab.grab()
        img.save(output_path)
        return True
    except Exception:
        return False

def capture_region(region: Tuple[int, int, int, int], output_path: str) -> bool:
    """
    Capture a specific region of the screen and save it to the specified path.

    Args:
        region: A tuple (left, top, right, bottom) specifying the region to capture.
        output_path: The file path where the screenshot will be saved.

    Returns:
        True if the screenshot was saved successfully, False otherwise.
    """
    if ImageGrab is None:
        return False
    try:
        img = ImageGrab.grab(bbox=region)
        img.save(output_path)
        return True
    except Exception:
        return False

def load_screenshot(path: str) -> Optional["Image.Image"]:
    """
    Load a screenshot image from the specified path.

    Args:
        path: The file path of the image to load.

    Returns:
        The loaded PIL Image object, or None if loading fails.
    """
    if Image is None or not os.path.exists(path):
        return None
    try:
        return Image.open(path)
    except Exception:
        return None