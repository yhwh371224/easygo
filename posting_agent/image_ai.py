import requests
from openai import OpenAI
from django.conf import settings
from PIL import Image
import io

def generate_post_image(alt_text: str, filename_slug: str):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.images.generate(
        model="dall-e-3",
        prompt="...",
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    img_response = requests.get(image_url)
    img_response.raise_for_status()

    # ✅ WebP 변환으로 용량 최적화 (페이지 속도 개선)
    image = Image.open(io.BytesIO(img_response.content))
    output = io.BytesIO()
    image.save(output, format="WebP", quality=85)

    return {
        "image_bytes": output.getvalue(),
        "filename": f"{filename_slug}.webp",  # ✅ 의미 있는 파일명
        "alt_text": alt_text,                 # ✅ alt 태그용 텍스트
        "content_type": "image/webp",
    }