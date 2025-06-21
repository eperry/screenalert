"""
Utility functions for Screen Region Monitor.

Includes helpers for timer row coloring and other reusable logic.
"""

from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk

def create_rotated_text_image(text, width, height, color="#fff", bgcolor=None, font_size=18):
    img = Image.new("RGBA", (width, height), bgcolor or (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width, text_height = font.getsize(text)
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), text, font=font, fill=color)
    img = img.rotate(90, expand=1)
    return img

def get_timer_row_color(
    remaining: int,
    total: int,
    warning_threshold: float,
    alert_threshold: float,
    warning_color: str,
    alert_color: str
) -> Optional[str]:
    """
    Determine the color for a timer row based on warning and alert thresholds.

    Args:
        remaining: Seconds left on the timer.
        total: Total seconds for the timer.
        warning_threshold: Fraction (0-1) for warning color.
        alert_threshold: Fraction (0-1) for alert color.
        warning_color: Color for warning (e.g., "#FFD700").
        alert_color: Color for alert (e.g., "#FF3333").

    Returns:
        The color string for the row, or None for default color.
    """
    if total == 0:
        return None
    percent_left = remaining / total
    if percent_left <= alert_threshold:
        return alert_color
    if percent_left <= warning_threshold:
        return warning_color
    return None

def render_status_rotated(
    canvas: tk.Canvas,
    text: str,
    width: int,
    height: int,
    color: str,
    bgcolor: str,
    font_size: int
) -> None:
    """
    Render rotated status text (vertical) in the given canvas, using the provided font size.
    """
    margin = 2
    img_status = create_rotated_text_image(
        text,
        width - 2 * margin,
        height - 2 * margin,
        color=color,
        bgcolor=bgcolor,
        font_size=font_size
    )
    imgtk = ImageTk.PhotoImage(img_status)
    canvas.create_image(
        width // 2,
        height // 2,
        anchor="center",
        image=imgtk
    )
    # Prevent garbage collection
    if not hasattr(render_status_rotated, "_img_refs"):
        render_status_rotated._img_refs = []
    render_status_rotated._img_refs.append(imgtk)

def get_max_status_font_size(
    words: List[str],
    width: int,
    height: int,
    font_path: str = "arial.ttf",
    margin: int = 2
) -> int:
    """
    Returns the largest font size that allows all given words to fit (rotated) in the box.
    """
    from PIL import ImageFont, ImageDraw, Image
    min_font, max_font = 8, height
    for font_size in range(max_font, min_font - 1, -1):
        fits = True
        for word in words:
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                font = ImageFont.load_default()
            # Create a dummy image to measure
            img = Image.new("RGBA", (width, height))
            draw = ImageDraw.Draw(img)
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), word, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width, text_height = font.getsize(word)
            # After rotation, width/height swap
            if text_height + 2 * margin > width or text_width + 2 * margin > height:
                fits = False
                break
        if fits:
            return font_size
    return min_font

def get_max_rotated_font_size(
    text: str,
    width: int,
    height: int,
    font_family: str = "Segoe UI",
    font_weight: str = "bold",
    margin: int = 6
) -> int:
    """
    Returns the largest font size that allows the rotated text to fit in the given box.

    Args:
        text: The text to display.
        width: The width of the box.
        height: The height of the box.
        font_family: The font family to use.
        font_weight: The font weight to use.
        margin: Margin in pixels to leave around the text.

    Returns:
        The maximum font size that fits.
    """
    root = tk.Tk()
    root.withdraw()
    max_size = min(width, height)
    for size in range(max_size, 4, -1):
        font = (font_family, size, font_weight)
        canvas = tk.Canvas(root)
        text_id = canvas.create_text(0, 0, text=text, font=font, anchor="nw", angle=90)
        bbox = canvas.bbox(text_id)
        canvas.destroy()
        if bbox:
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            if text_width + margin <= width and text_height + margin <= height:
                root.destroy()
                return size
    root.destroy()
    return 8  # fallback minimum