from django.conf import settings
import anthropic

TOPICS = [
    ("sydney-airport-pickup-tips", "Sydney Airport Pickup Tips", "시드니 공항 픽업 팁"),
    ("early-morning-flight-sydney", "Early Morning Flight Sydney Airport Transfer", "새벽 비행기 시드니 공항 픽업"),
    ("sydney-airport-terminals", "Sydney Airport T1 T2 T3 Terminal Guide", "시드니 공항 터미널 가이드"),
    ("airport-to-city-sydney", "Sydney Airport to City Transfer Guide", "시드니 공항에서 시티까지"),
    ("family-airport-transfer", "Family Airport Transfer Sydney Tips", "가족 공항 픽업 팁"),
    ("business-travel-sydney-airport", "Business Travel Sydney Airport Shuttle", "비즈니스 출장 시드니 공항 셔틀"),
]


def pick_topic():
    """발행 이력 기반으로 안 쓴 토픽 선택"""
    from posting_agent.models import BlogPost
    used_slugs = BlogPost.objects.values_list('slug', flat=True)
    for slug, title_en, title_ko in TOPICS:
        if not any(slug in s for s in used_slugs):
            return slug, title_en
    # 전부 사용했으면 첫 번째로 순환
    return TOPICS[0][0], TOPICS[0][1]


def generate_all_content(topic_slug: str, topic_title: str):
    """SEO 롱폼 + 소셜 + GMB 글 한 번에 생성"""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are a content writer for EasyGo Airport Shuttle, a professional airport transfer service in Sydney, Australia.

Generate THREE versions of content for the topic: "{topic_title}"

Return ONLY this exact format, no extra text:

===SEO===
[Write a 300-400 word SEO blog post. Include H2 subheadings. Natural keyword usage: Sydney airport pickup, airport transfer Sydney, EasyGo shuttle. Professional and helpful tone.]

===SOCIAL===
[Write a 2-3 sentence Facebook/Instagram post. Engaging, friendly tone. End with a call to action. Include 3-5 relevant hashtags.]

===GMB===
[Write 2 sentences for Google Business Profile. Professional, local focus. No hashtags.]

===ALT===
[Write one image alt text describing a professional airport shuttle scene relevant to this topic. Under 15 words.]

===TITLE===
[Write an SEO-optimized blog post title. Under 60 characters.]"""
        }]
    )

    raw = message.content[0].text.strip()
    return parse_content(raw, topic_slug)


def parse_content(raw: str, topic_slug: str):
    """응답 파싱"""
    def extract(tag):
        start = raw.find(f"==={tag}===")
        if start == -1:
            return ""
        start += len(f"==={tag}===")
        end = raw.find("===", start)
        return raw[start:end].strip() if end != -1 else raw[start:].strip()

    return {
        "topic_slug": topic_slug,
        "title": extract("TITLE"),
        "seo_content": extract("SEO"),
        "social_content": extract("SOCIAL"),
        "gmb_content": extract("GMB"),
        "image_alt": extract("ALT"),
    }