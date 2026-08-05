from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Post, Category, Tag


def post_list(request):
    posts = Post.objects.filter(status='published').select_related('category')

    # 지역 필터링: ?region= 쿼리(지역 홈페이지에서 넘어온 경우) 우선,
    # 없으면 URL 경로 기반 지역을 사용, 그마저 없으면 시드니를 기본값으로 사용.
    # regions가 비어 있는 글(범용 글)은 어느 지역에서든 함께 노출된다.
    region_slug = request.GET.get('region', '').strip()
    active_region_slug = (
        region_slug or getattr(getattr(request, 'region', None), 'slug', '') or 'sydney'
    )
    posts = posts.filter(
        Q(regions__isnull=True) | Q(regions__slug=active_region_slug)
    ).distinct()

    # 검색
    query = request.GET.get('q', '').strip()
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(content__icontains=query)
        )

    # 카테고리 필터
    category_slug = request.GET.get('category', '').strip()
    current_category = None
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug).first()
        if current_category:
            posts = posts.filter(category=current_category)

    # 태그 필터
    tag_slug = request.GET.get('tag', '').strip()
    if tag_slug:
        posts = posts.filter(tags__slug=tag_slug)

    # 추천 글 (목록 상단 featured card 용)
    featured_post = posts.filter(is_featured=True).first()

    # 페이지네이션 (featured 글은 목록에서 제외)
    post_qs = posts.exclude(is_featured=True) if featured_post else posts
    paginator = Paginator(post_qs, 9)
    page      = request.GET.get('page', 1)
    posts_page = paginator.get_page(page)

    context = {
        'posts'            : posts_page,
        'featured_post'    : featured_post,
        'categories'       : Category.objects.all(),
        'query'            : query,
        'category_slug'    : category_slug,
        'current_category' : current_category,
        'tag_slug'         : tag_slug,
        'region_slug'      : region_slug,
    }
    return render(request, 'articles/blog_list.html', context)


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')

    # 조회수 증가
    Post.objects.filter(pk=post.pk).update(view_count=post.view_count + 1)

    # 관련 글 - 같은 카테고리, 최신 4개
    related_posts = Post.objects.filter(
        status='published',
        category=post.category,
    ).exclude(pk=post.pk).order_by('-published_at')[:4]

    # 최신 글 사이드바용 5개
    recent_posts = Post.objects.filter(
        status='published'
    ).exclude(pk=post.pk).order_by('-published_at')[:5]

    context = {
        'post'          : post,
        'related_posts' : related_posts,
        'recent_posts'  : recent_posts,
    }
    return render(request, 'articles/blog_detail.html', context)
