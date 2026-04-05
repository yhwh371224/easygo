import io
import random

import requests
from django.conf import settings
from PIL import Image


def _unsplash_random_fallback() -> str | None:
    """Fetch a completely random image URL from Unsplash."""
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
    """
    Fetch an image for a post in the following priority:
    1. Unsplash search (query-based, random from top 10)
    2. Unsplash completely random (/photos/random)
    3. Raise ValueError
    """
    search_query = query or "sydney airport transfer shuttle"

    # Step 1: Unsplash search (up to 2 queries)
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

    # Step 2: Unsplash completely random
    if not image_url:
        image_url = _unsplash_random_fallback()

    if not image_url:
        raise ValueError(f"All image sources failed: {search_query}")

    # Download and convert to WebP
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