import os
import time
import uuid
import textwrap

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageStat


def create_verse_image(verse_text, uploaded_image=None):
    bg_dir = os.path.join(settings.BASE_DIR, 'static', 'verse_backgrounds')
    default_bg = os.path.join(bg_dir, 'default.webp')

    if uploaded_image and os.path.exists(uploaded_image):
        img = Image.open(uploaded_image).convert("RGB")
    elif os.path.exists(default_bg):
        img = Image.open(default_bg).convert("RGB")
    else:
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), color=(255, 255, 255))

    max_width, max_height = 1920, 1080
    W, H = img.size
    if W > max_width or H > max_height:
        ratio = min(max_width / W, max_height / H)
        img = img.resize((int(W * ratio), int(H * ratio)), Image.LANCZOS)
        W, H = img.size

    draw = ImageDraw.Draw(img)

    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSansKR-Regular.ttf')
    max_font_size = H // 16
    min_font_size = 10
    font_size = max_font_size
    max_width_ratio = 0.9
    max_height_ratio = 0.9

    output_dir = os.path.join(settings.MEDIA_ROOT, 'verse')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex[:8]
    webp_path = os.path.join(output_dir, f"verse_{timestamp}_{unique_id}.webp")

    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, font_size)
        line_spacing = font_size // 4

        lines = []
        for raw_line in verse_text.split('\n'):
            wrapped = textwrap.wrap(raw_line, width=40)  
            lines.extend(wrapped)

        max_line_width = max(draw.textlength(line, font=font) for line in lines)
        total_text_height = len(lines) * (font_size + line_spacing)

        if max_line_width <= W * max_width_ratio and total_text_height <= H * max_height_ratio:
            break  
        font_size -= 3  

    total_text_height = len(lines) * (font_size + line_spacing)
    y_text = (H - total_text_height) // 2

    brightness = ImageStat.Stat(img).mean[0]
    text_color = "black" if brightness > 127 else "white"

    for line in lines:
        line_width = draw.textlength(line, font=font)
        x_text = (W - line_width) // 2
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += font_size + line_spacing

    img.save(webp_path, format='WEBP', quality=85)

    return f"verse_{timestamp}_{unique_id}.webp"
