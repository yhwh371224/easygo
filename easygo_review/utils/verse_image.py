import os
import time
import random
import uuid

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageStat


def create_verse_image(verse_text, uploaded_image=None):
    bg_dir = os.path.join(settings.BASE_DIR, 'static', 'verse_backgrounds')
    default_bg = os.path.join(bg_dir, 'default.webp')
    
    # 배경 이미지 선택
    if uploaded_image:
        img = Image.open(uploaded_image).convert("RGB")
    elif os.path.exists(default_bg):
        img = Image.open(default_bg).convert("RGB")
    else:
        raise FileNotFoundError("No background images available.")

    # 해상도 제한 (1920x1080 이상인 경우)
    max_width, max_height = 1920, 1080
    W, H = img.size
    if W > max_width or H > max_height:
        ratio = min(max_width / W, max_height / H)
        img = img.resize((int(W * ratio), int(H * ratio)), Image.LANCZOS)
        W, H = img.size

    draw = ImageDraw.Draw(img)

    # 폰트 경로
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSansKR-Regular.ttf')

    # 글씨 크기 자동 조정 
    max_font_size = H // 16  
    min_font_size = 10
    font_size = max_font_size
    max_width_ratio = 0.9
    max_height_ratio = 0.9

    # 출력 디렉토리
    output_dir = os.path.join(settings.MEDIA_ROOT, 'verse')
    os.makedirs(output_dir, exist_ok=True)

    # 파일명 timestamp
    timestamp = int(time.time() * 1000) 
    unique_id = uuid.uuid4().hex[:8] 
    webp_path = os.path.join(output_dir, f"verse_{timestamp}_{unique_id}.webp")

    # 글씨 크기 조정 루프
    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, font_size)
        line_spacing = font_size // 4

        raw_lines = verse_text.split('\n')
        lines = []
        for raw_line in raw_lines:
            words = raw_line.split()
            line = ""
            for word in words:
                test_line = line + " " + word if line else word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
                if line_width < W * max_width_ratio:
                    line = test_line
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)

        total_text_height = len(lines) * (font_size + line_spacing)
        if total_text_height < H * max_height_ratio:
            break
        font_size -= 3

    # 세로 중앙 정렬
    total_text_height = len(lines) * (font_size + line_spacing)
    y_text = (H - total_text_height) // 2

    # 배경 밝기에 따라 글자색 결정
    brightness = ImageStat.Stat(img).mean[0]
    text_color = "black" if brightness > 127 else "white"

    # 텍스트 출력
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x_text = (W - line_width) // 2
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += font_size + line_spacing

    # WebP 저장
    img.save(webp_path, format='WEBP', quality=85)

    return f"verse_{timestamp}.webp"