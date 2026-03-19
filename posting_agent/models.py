from django.db import models
from django.utils.text import slugify
from django.urls import reverse
import uuid


class BlogPost(models.Model):
    PLATFORM_STATUS = [
        ('pending', 'Pending'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    # 콘텐츠
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    seo_content = models.TextField(help_text="Django 블로그용 SEO 롱폼 글")
    social_content = models.TextField(help_text="Facebook/Instagram용 짧은 글")
    gmb_content = models.TextField(help_text="Google Business용 짧은 글")

    # 이미지
    image = models.ImageField(upload_to='blog_posts/', blank=True, null=True)
    image_alt = models.CharField(max_length=200, blank=True)

    # 발행 상태
    blog_status = models.CharField(max_length=20, choices=PLATFORM_STATUS, default='pending')
    facebook_status = models.CharField(max_length=20, choices=PLATFORM_STATUS, default='pending')
    instagram_status = models.CharField(max_length=20, choices=PLATFORM_STATUS, default='pending')
    gmb_status = models.CharField(max_length=20, choices=PLATFORM_STATUS, default='pending')

    # 메타
    created = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('posting_agent:blog_detail', kwargs={'slug': self.slug})

