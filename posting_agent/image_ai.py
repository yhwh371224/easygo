import io
import random

import requests
from django.conf import settings
from PIL import Image

from articles.models import Article


def _article_image_fallback() -> dict | None:
    """articles 앱에서 thumbnail이 있는 이미지를 랜덤으로 가져옴"""
    article = (
        Article.objects
        .exclude(thumbnail="")
        .exclude(thumbnail=None)
        .order_by("?")
        .first()
    )

    if not article:
        return None

    thumbnail = article.thumbnail

    try:
        with open(thumbnail.path, "rb") as f:
            image_bytes = f.read()
    except (FileNotFoundError, ValueError, OSError):
        return None

    image = Image.open(io.BytesIO(image_bytes))
    output = io.BytesIO()
    image.save(output, format="WebP", quality=85)

    return {
        "image_bytes": output.getvalue(),
        "filename": None,
        "alt_text": None,
        "content_type": "image/webp",
        "source_url": thumbnail.url,
    }


def _unsplash_random_fallback() -> str | None:
    """쿼리 없이 Unsplash 완전 랜덤 이미지 URL 반환"""
    try:
        response = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"orientation": "landscape"},
            headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["urls"]["regular"]
    except Exception:
        return None


def generate_post_image(alt_text: str, filename_slug: str, query: str = None):
    search_query = query or "sydney airport transfer shuttle"

    # 1단계: Unsplash 검색 (query 기반, 최대 2번 시도)
    queries = [search_query, "sydney airport shuttle transfer"]
    image_url = None

    for q in queries:
        try:
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": q, "per_page": 10, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
                timeout=10,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                image_url = random.choice(results)["urls"]["regular"]
                break
        except Exception:
            continue

    if image_url:
        try:
            img_response = requests.get(image_url, timeout=10)
            img_response.raise_for_status()

            image = Image.open(io.BytesIO(img_response.content))
            output = io.BytesIO()
            image.save(output, format="WebP", quality=85)

            return {
                "image_bytes": output.getvalue(),
                "filename": f"{filename_slug}.webp",
                "alt_text": alt_text,
                "content_type": "image/webp",
                "source_url": image_url,
            }
        except Exception:
            pass

    # 2단계: articles 앱 thumbnail 랜덤 선택
    fallback = _article_image_fallback()
    if fallback:
        fallback["filename"] = f"{filename_slug}.webp"
        fallback["alt_text"] = alt_text
        return fallback

    # 3단계: Unsplash 완전 랜덤
    random_url = _unsplash_random_fallback()
    if random_url:
        try:
            img_response = requests.get(random_url, timeout=10)
            img_response.raise_for_status()

            image = Image.open(io.BytesIO(img_response.content))
            output = io.BytesIO()
            image.save(output, format="WebP", quality=85)

            return {
                "image_bytes": output.getvalue(),
                "filename": f"{filename_slug}.webp",
                "alt_text": alt_text,
                "content_type": "image/webp",
                "source_url": random_url,
            }
        except Exception:
            pass

    raise ValueError(f"모든 이미지 소스에서 실패했어요: {search_query}")