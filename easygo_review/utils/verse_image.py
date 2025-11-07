import os
import time
import uuid
import textwrap
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageStat


def create_verse_image(verse_text, uploaded_image=None):
    # ----------------------------
    # 1. Background selection
    # ----------------------------
    bg_dir = os.path.join(settings.BASE_DIR, 'static', 'verse_backgrounds')
    default_bg = os.path.join(bg_dir, 'default.webp')

    if uploaded_image and os.path.exists(uploaded_image):
        img = Image.open(uploaded_image).convert("RGB")
    elif os.path.exists(default_bg):
        img = Image.open(default_bg).convert("RGB")
    else:
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), color=(255, 255, 255))

    # ----------------------------
    # 2. Resize (keep under 1920x1080)
    # ----------------------------
    max_width, max_height = 1920, 1080
    W, H = img.size
    if W > max_width or H > max_height:
        ratio = min(max_width / W, max_height / H)
        img = img.resize((int(W * ratio), int(H * ratio)), Image.LANCZOS)
        W, H = img.size

    # ----------------------------
    # 3. Font setup
    # ----------------------------
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSansKR-Regular.ttf')
    font_size = int(H * 0.06)  # 6% of image height
    if len(verse_text) > 200:
        font_size = int(H * 0.045)  # smaller if too long

    font = ImageFont.truetype(font_path, font_size)
    line_spacing = int(font_size * 0.3)
    draw = ImageDraw.Draw(img)

    # ----------------------------
    # 4. Text wrapping and layout
    # ----------------------------
    lines = []
    wrap_width = 40 if W > 1000 else 25  # wrap width depends on image size
    for raw_line in verse_text.split("\n"):
        wrapped = textwrap.wrap(raw_line, width=wrap_width)
        lines.extend(wrapped)

    total_text_height = len(lines) * (font_size + line_spacing)
    y_text = (H - total_text_height) // 2

    # ----------------------------
    # 5. Determine text color (auto black/white)
    # ----------------------------
    brightness = ImageStat.Stat(img).mean[0]
    text_color = "black" if brightness > 127 else "white"

    # ----------------------------
    # 6. Draw text
    # ----------------------------
    for line in lines:
        line_width = draw.textlength(line, font=font)
        x_text = (W - line_width) // 2
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += font_size + line_spacing

    # ----------------------------
    # 7. Save image
    # ----------------------------
    output_dir = os.path.join(settings.MEDIA_ROOT, 'verse')
    os.makedirs(output_dir, exist_ok=True)

    timestamp = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex[:8]
    webp_filename = f"verse_{timestamp}_{unique_id}.webp"
    webp_path = os.path.join(output_dir, webp_filename)

    img.save(webp_path, format='WEBP', quality=85)

    return webp_filename
