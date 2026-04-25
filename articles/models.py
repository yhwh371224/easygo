from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import math


class Category(models.Model):
    name        = models.CharField(max_length=100, verbose_name='Categories')
    slug        = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    description = models.TextField(blank=True, verbose_name='Description')
    order       = models.PositiveIntegerField(default=0, verbose_name='Order')

    class Meta:
        verbose_name        = 'Category'
        verbose_name_plural = 'Categories'
        ordering            = ['order', 'name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=80, verbose_name='Tag')
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)

    class Meta:
        verbose_name        = 'Tag'
        verbose_name_plural = 'Tags'
        ordering            = ['name']

    def __str__(self):
        return self.name


class Post(models.Model):

    # ── 기본 정보 ──────────────────────────────
    title     = models.CharField(max_length=200, verbose_name='Post')
    slug      = models.SlugField(max_length=220, unique=True, allow_unicode=True,
                                 help_text='Used in URL. Auto-generated from title if left blank.')
    excerpt   = models.TextField(max_length=300, blank=True, verbose_name='Excerpt',
                                 help_text='Short summary displayed on list pages (300 characters max)')
    content   = models.TextField(verbose_name='Content (HTML)')

    # ── 분류 ───────────────────────────────────
    category  = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                  null=True, blank=True,
                                  related_name='posts', verbose_name='Category')
    tags      = models.ManyToManyField(Tag, blank=True,
                                       related_name='posts', verbose_name='Tag')

    # ── 이미지 ─────────────────────────────────
    thumbnail = models.ImageField(upload_to='articles/thumbnails/%Y/%m/',
                                  null=True, blank=True, verbose_name='Thumbnail')
    thumbnail_query = models.CharField(max_length=100, blank=True,
                                       verbose_name='Thumbnail Query',
                                       help_text='Search keyword for Unsplash')
    thumbnail_source_url = models.URLField(max_length=500, blank=True,  # 추가
                                           verbose_name='Thumbnail Source URL',
                                           help_text='Original Unsplash image URL for GMB posting.')

    # ── SEO ────────────────────────────────────
    meta_title       = models.CharField(max_length=70, blank=True,
                                        verbose_name='SEO Post',
                                        help_text='Overrides title in search results (max 70 chars).')
    meta_description = models.CharField(max_length=500, blank=True,
                                        verbose_name='SEO Description',
                                        help_text='Displayed in Google search results (max 160 chars).')

    # ── 상태 ───────────────────────────────────
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('published', 'Published'),
    ]
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES,
                                   default='draft', verbose_name='Status')
    is_featured = models.BooleanField(default=False, verbose_name='Featured Post',
                                      help_text='Pin this post at the top of the blog listing.')

    # ── SNS 발행 상태 (posting_agent 연동) ──────
    posted_to_google    = models.BooleanField(default=False, verbose_name='Posted to Google Business')
    posted_to_facebook  = models.BooleanField(default=False, verbose_name='Posted to Facebook')
    posted_to_instagram = models.BooleanField(default=False, verbose_name='Posted to Instagram')

    gmb_content = models.TextField(blank=True, null=True, verbose_name='GMB content', help_text='비워두면 AI가 자동으로 1500자 이내로 요약합니다.', max_length=1500,)

    # ── 통계 ───────────────────────────────────
    view_count = models.PositiveIntegerField(default=0, verbose_name='View Count')

    # ── 날짜 ───────────────────────────────────
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at   = models.DateTimeField(auto_now=True,     verbose_name='Updated At')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Published At')

    class Meta:
        verbose_name        = 'Post'
        verbose_name_plural = 'Posts'
        ordering            = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    # ── slug 자동 생성 ──────────────────────────
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    # ── SEO 헬퍼 ───────────────────────────────
    def get_meta_title(self):
        return self.meta_title or self.title

    def get_meta_description(self):
        return self.meta_description or self.excerpt

    # ── 읽기 시간 자동 계산 (분) ────────────────
    @property
    def read_time(self):
        word_count = len(self.content.split())
        minutes = math.ceil(word_count / 200)
        return max(1, minutes)

    # ── posting_agent 에서 쓸 헬퍼 ─────────────
    @property
    def is_fully_posted(self):
        """Returns True if posted to all three SNS channels."""
        return all([
            self.posted_to_google,
            self.posted_to_facebook,
            self.posted_to_instagram,
        ])