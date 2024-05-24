from django.shortcuts import render, redirect
from .models import Post, Category, Tag, Comment
from .forms import CommentForm
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q


class PostList(ListView):
    model = Post
    template_name = 'easygo_review/post_list.html'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        context['category_list'] = Category.objects.all()
        context['posts_without_category'] = Post.objects.filter(category=None).count()

        return context


class PostSearch(PostList):
    def get_queryset(self):
        q = self.kwargs['q']
        object_list = Post.objects.filter(Q(title__contains=q) | Q(content__contains=q))
        return object_list

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostSearch, self).get_context_data()
        context['search_info'] = 'Search: "{}"'.format(self.kwargs['q'])
        return context


class PostDetail(DetailView):
    model = Post
    template_name = 'easygo_review/post_detail.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostDetail, self).get_context_data(**kwargs)
        context['category_list'] = Category.objects.all()
        context['posts_without_category'] = Post.objects.filter(category=None).count()
        context['comment_form'] = CommentForm()

        return context


class PostCreate(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'easygo_review/post_form.html'
    fields = [
        'title', 'content', 'head_image', 'category', 'tags'
    ]

    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated:
            form.instance.author = current_user
            return super(type(self), self).form_valid(form)
        else:
            return redirect('/easygo_review/')


class PostUpdate(UpdateView):
    model = Post
    template_name = 'easygo_review/post_form.html'
    fields = [
        'title', 'content', 'head_image', 'category', 'tags'
    ]


class PostListByTag(ListView):
    def get_queryset(self):
        tag_slug = self.kwargs['slug']
        tag = Tag.objects.get(slug=tag_slug)

        return tag.post_set.order_by('-created')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(type(self), self).get_context_data(**kwargs)
        context['category_list'] = Category.objects.all()
        context['posts_without_category'] = Post.objects.filter(category=None).count()
        tag_slug = self.kwargs['slug']
        context['tag'] = Tag.objects.get(slug=tag_slug)

        return context


class PostListByCategory(ListView):

    def get_queryset(self):
        slug = self.kwargs['slug']

        if slug == '_none':
            category = None
        else:
            category = Category.objects.get(slug=slug)

        return Post.objects.filter(category=category).order_by('-created')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(type(self), self).get_context_data(**kwargs)
        context['category_list'] = Category.objects.all()
        context['posts_without_category'] = Post.objects.filter(category=None).count()

        slug = self.kwargs['slug']

        if slug == '_none':
            context['category'] = 'no category'
        else:
            category = Category.objects.get(slug=slug)
            context['category'] = category

        # context['title'] = 'easygo_review - {}'.format(category.name)
        return context


def new_comment(request, pk):
    post = Post.objects.get(pk=pk)

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect(comment.get_absolute_url())
    else:
        return redirect('/easygo_review/')


class CommentUpdate(UpdateView):
    model = Comment
    form_class = CommentForm

    def get_object(self, queryset=None):
        comment = super(CommentUpdate, self).get_object()
        if comment.author != self.request.user:
            raise PermissionError('Comment No right to edit')
        return comment


def delete_comment(request, pk):
    comment = Comment.objects.get(pk=pk)
    post = comment.post
    if request.user == comment.author:
        comment.delete()
        return redirect(post.get_absolute_url() + '#comment-list')
    else:
        raise PermissionError('Comment: No right to delete')

# class CommentDelete(DeleteView):
#     model = Comment
#
#     def get_object(self, queryset=None):
#         comment = super(CommentDelete, self).get_object()
#         if comment.author != self.request.user:
#             raise PermissionError('Comment 삭제 권한이 없습니다.')
#         return comment
#
#     def get_success_url(self):
#         post = self.get_object().post
#         return post.get_absolute_url() + '#comment-list'

# def post_detail(request, pk):
#     easygo_review_post = Post.objects.get(pk=pk)
#
#     return render(
#         request,
#         'easygo_review/post_detail.html',
#         {
#             'easygo_review_post': easygo_review_post,
#         }
#     )

# def index(request):
#     posts = Post.objects.all()
#
#     return render(
#         request,
#         'easygo_review/index.html',
#         {
#             'posts': posts,
#         }
#     )
