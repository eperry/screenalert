"""
Screenshot utility module for Screen Region Monitor.

Provides functions to capture screenshots of the entire screen or specific regions.
"""

from typing import Tuple, Optional
import os
import pyautogui
from PIL import ImageGrab, Image

def take_full_screenshot():
    try:
        return pyautogui.screenshot()
    except Exception as e:
        print(f"Screen capture failed: {e}")
        screen_width, screen_height = pyautogui.size()
        return Image.new("RGB", (screen_width, screen_height), color="#222")

def crop_region(full_img: Image.Image, coords: tuple[int, int, int, int]) -> Image.Image:
    """
    Crop a region from the full screenshot.

    Args:
        full_img: The full screenshot as a PIL Image.
        coords: (left, top, width, height) tuple.

    Returns:
        Cropped region as a PIL Image.
    """
    left, top, width, height = coords
    return full_img.crop((left, top, left + width, top + height))

def create_thumbnail(region_img: Image.Image, thumb_size: tuple[int, int]) -> Image.Image:
    """
    Create a thumbnail of the region image, maintaining aspect ratio.

    Args:
        region_img: The region image as a PIL Image.
        thumb_size: (width, height) tuple for the thumbnail.

    Returns:
        Thumbnail as a PIL Image.
    """
    thumb = region_img.copy()
    thumb.thumbnail(thumb_size, Image.LANCZOS)
    return thumb

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