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