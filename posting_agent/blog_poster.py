from django.core.files.base import ContentFile
from django.utils import timezone
from posting_agent.models import BlogPost

def save_blog_post(content: dict, image_bytes: bytes, filename: str) -> BlogPost:
    post = BlogPost(
        title=content['title'],
        slug=content['topic_slug'],  # 추가!
        seo_content=content['seo_content'],
        social_content=content['social_content'],
        gmb_content=content['gmb_content'],
        image_alt=content['image_alt'],
        blog_status='published',
        published_at=timezone.now(),
    )
    post.save()
    if image_bytes:
        post.image.save(filename, ContentFile(image_bytes), save=True)
    return post
