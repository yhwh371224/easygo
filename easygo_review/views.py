from django.shortcuts import render, redirect
from .models import Post, Comment
from .forms import CommentForm, PostForm
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q


class PostList(ListView):
    model = Post
    template_name = 'easygo_review/post_list.html'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)       
        context['post_count'] = Post.objects.all().count()
        posts_with_ratings = [{
            'p': p,
            'rating': p.rating,
            'rating_range': range(p.rating),
            'remaining_range': range(5 - p.rating)
        } for p in context['object_list']]
        context['posts_with_ratings'] = posts_with_ratings

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
        context['post_count'] = Post.objects.all().count()
        context['comment_form'] = CommentForm()

        return context


class PostCreate(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'easygo_review/post_form.html'
    fields = ['name', 'date', 'link', 'content', 'rating']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_guide'] = 'Please post your review'
        return context

    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated:
            form.instance.author = current_user
            rating = form.cleaned_data.get('rating')
            if not (1 <= rating <= 5):
                form.add_error('rating', 'Rating must be between 1 and 5')
                return self.form_invalid(form)
            return super(type(self), self).form_valid(form)
        else:
            return redirect('/easygo_review/')


class PostUpdate(UpdateView):
    model = Post
    template_name = 'easygo_review/post_form.html'
    fields = ['content']


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
            raise PermissionError('No right to edit')
        return comment


def delete_comment(request, pk):
    comment = Comment.objects.get(pk=pk)
    post = comment.post
    if request.user == comment.author:
        comment.delete()
        return redirect(post.get_absolute_url() + '#comment-list')
    else:
        raise PermissionError('No right to delete')


class CommentDelete(DeleteView):
    model = Comment

    def get_object(self, queryset=None):
        comment = super(CommentDelete, self).get_object()
        if comment.author != self.request.user:
            raise PermissionError('No right to delete Comment')
        return comment

    def get_success_url(self):
        post = self.get_object().post
        return post.get_absolute_url() + '#comment-list'
    

def post_detail(request, pk):
    easygo_review_post = Post.objects.get(pk=pk)

    return render(
        request,
        'easygo_review/post_detail.html',
        {
            'easygo_review_post': easygo_review_post,
        }
    )


def index(request):
    posts = Post.objects.all()

    return render(
        request,
        'easygo_review/index.html',
        {
            'posts': posts,
        }
    )
