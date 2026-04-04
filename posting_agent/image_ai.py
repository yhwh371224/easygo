import requests
from django.conf import settings
from PIL import Image
import io


def generate_post_image(alt_text: str, filename_slug: str, query: str = None):
    search_query = query or alt_text

    # Unsplash API로 이미지 검색
    response = requests.get(
        "https://api.unsplash.com/search/photos",
        params={
            "query": search_query,
            "per_page": 1,
            "orientation": "landscape",
        },
        headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    if not results:
        raise ValueError(f"Unsplash에서 이미지를 찾을 수 없어요: {search_query}")

    image_url = results[0]["urls"]["regular"]

    # 이미지 다운로드
    img_response = requests.get(image_url)
    img_response.raise_for_status()

    # WebP 변환
    image = Image.open(io.BytesIO(img_response.content))
    output = io.BytesIO()
    image.save(output, format="WebP", quality=85)

    return {
        "image_bytes": output.getvalue(),
        "filename": f"{filename_slug}.webp",
        "alt_text": alt_text,
        "content_type": "image/webp",
    }