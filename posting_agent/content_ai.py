from django.conf import settings
import anthropic

TOPICS = [
    # ✅ 이미 발행됨 - 건너뜀
    # ("sydney-airport-to-cbd-transfer-guide", ...),
    # ("sydney-airport-pickup-fees-explained", ...),
    # ("maxi-taxi-vs-uber-at-sydney-airport-what-nobody-tells-you-about-group-travel", ...),

    # 남은 9개
    ("sydney-airport-international-terminal-arrivals-guide", "The Complete Guide to Sydney Airport International Terminal (T1) Arrivals"),
    ("sydney-airport-domestic-terminal-t2-t3-pickup", "Sydney Airport Domestic Terminal Pickup: T2 vs T3 – What's the Difference?"),
    ("how-early-leave-for-sydney-airport-by-suburb", "How Early Should You Leave for Sydney Airport? A Suburb-by-Suburb Guide"),
    ("north-shore-sydney-airport-transfer", "North Shore to Sydney Airport: The Fastest and Cheapest Options in 2025"),
    ("child-seats-sydney-airport-transfer", "Travelling with Kids? Everything You Need to Know About Child Seats on Airport Transfers"),
    ("western-sydney-airport-transfer-guide", "Western Sydney to the Airport: Why a Private Transfer Makes Sense"),
    ("flight-delay-airport-pickup-sydney", "What Happens If Your Flight Is Delayed? How EasyGo Handles It"),
    ("sydney-airport-to-hotel-cbd-transfer", "Sydney Airport to Hotel: Which CBD Hotels Are Easiest to Get To?"),
    ("inner-west-sydney-airport-transfer", "Inner West Sydney Airport Transfers: Suburbs, Pricing & Tips"),
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