"""
Utility functions for Screen Region Monitor.

Includes helpers for timer row coloring and other reusable logic.
"""

from typing import Optional
from PIL import Image, ImageDraw, ImageFont

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