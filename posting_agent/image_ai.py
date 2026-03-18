import requests
from openai import OpenAI
from django.conf import settings


def generate_post_image():
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.images.generate(
        model="dall-e-3",
        prompt="A clean, modern airport shuttle van at Sydney Airport at sunrise. Professional, welcoming atmosphere. Photorealistic style.",
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url

    # 이미지 다운로드
    img_response = requests.get(image_url)
    img_response.raise_for_status()

    return img_response.content  # bytes 반환