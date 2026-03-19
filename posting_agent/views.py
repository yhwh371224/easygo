from django.shortcuts import render, get_object_or_404
from posting_agent.models import BlogPost


def blog_list(request):
    posts = BlogPost.objects.filter(blog_status='published')
    return render(request, 'posting_agent/blog_list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, blog_status='published')
    return render(request, 'posting_agent/blog_detail.html', {'post': post})
