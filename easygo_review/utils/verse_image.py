import os
import time
import uuid
import textwrap

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageStat


def create_verse_image(verse_text, uploaded_image=None):
    # ----------------------------
    # 배경 이미지 선택
    # ----------------------------
    bg_dir = os.path.join(settings.BASE_DIR, 'static', 'verse_backgrounds')
    default_bg = os.path.join(bg_dir, 'default.webp')

    if uploaded_image and os.path.exists(uploaded_image):
        img = Image.open(uploaded_image).convert("RGB")
    elif os.path.exists(default_bg):
        img = Image.open(default_bg).convert("RGB")
    else:
        # fallback: 단색 흰색 배경
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), color=(255, 255, 255))

    # ----------------------------
    # 해상도 제한
    # ----------------------------
    max_width, max_height = 1920, 1080
    W, H = img.size
    if W > max_width or H > max_height:
        ratio = min(max_width / W, max_height / H)
        img = img.resize((int(W * ratio), int(H * ratio)), Image.LANCZOS)
        W, H = img.size

    draw = ImageDraw.Draw(img)

    # ----------------------------
    # 폰트 설정
    # ----------------------------
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSansKR-Regular.ttf')
    max_font_size = H // 12
    min_font_size = 10
    font_size = max_font_size
    max_width_ratio = 0.9
    max_height_ratio = 0.95

    # ----------------------------
    # 출력 디렉토리 및 파일명
    # ----------------------------
    output_dir = os.path.join(settings.MEDIA_ROOT, 'verse')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex[:8]
    webp_path = os.path.join(output_dir, f"verse_{timestamp}_{unique_id}.webp")

    # ----------------------------
    # 글자 크기 최대화
    # ----------------------------
    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, font_size)
        line_spacing = font_size // 4

        # textwrap로 줄 나누기
        lines = []
        for raw_line in verse_text.split('\n'):
            wrapped = textwrap.wrap(raw_line, width=40)  # 글자 수 제한
            lines.extend(wrapped)

        # 최대 줄 너비 및 전체 높이 계산
        max_line_width = max(draw.textlength(line, font=font) for line in lines)
        total_text_height = len(lines) * (font_size + line_spacing)

        # 이미지에 맞는지 체크
        if max_line_width <= W * max_width_ratio and total_text_height <= H * max_height_ratio:
            break  # 적합한 글씨 크기
        font_size -= 2  # 글자 크기 줄여 다시 계산

    # ----------------------------
    # 세로 중앙 정렬
    # ----------------------------
    total_text_height = len(lines) * (font_size + line_spacing)
    y_text = (H - total_text_height) // 2

    # ----------------------------
    # 글자색 결정 (배경 밝기 기준)
    # ----------------------------
    brightness = ImageStat.Stat(img).mean[0]
    text_color = "black" if brightness > 127 else "white"

    # ----------------------------
    # 텍스트 출력
    # ----------------------------
    for line in lines:
        line_width = draw.textlength(line, font=font)
        x_text = (W - line_width) // 2
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += font_size + line_spacing

    # ----------------------------
    # WebP 저장
    # ----------------------------
    img.save(webp_path, format='WEBP', quality=85)

    # ----------------------------
    # 정확한 파일명 반환
    # ----------------------------
    return f"verse_{timestamp}_{unique_id}.webp"
