from django.shortcuts import render, redirect
from .models import Post, Comment
from .forms import CommentForm, PostForm
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from blog.tasks import send_notification_email
from easygo_review.models import Post as EasygoPost
from main.settings import RECIPIENT_EMAIL
from blog.models import Post


def custom_login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        post = Post.objects.filter(email=email).first()
        if post:
            request.session['post_id'] = post.id
            return redirect('easygo_review:easygo_review')
        else:
            return render(request, 'easygo_review/custom_login.html', {'error': 'Invalid email address'})
    return render(request, 'easygo_review/custom_login.html')


def get_authenticated_post(request):
    post_id = request.session.get('post_id')
    if post_id:
        try:
            return Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return None
    return None


class PostList(ListView):
    model = EasygoPost
    template_name = 'easygo_review/post_list.html'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        context['post_count'] = EasygoPost.objects.all().count()

        for post in context['object_list']:
            if post.rating is None:
                post.rating = 5

        send_notification_email.delay(RECIPIENT_EMAIL)

        return context
    

class PostSearch(PostList):
    def get_queryset(self):
        q = self.kwargs['q']
        try:
            object_list = Post.objects.filter(Q(title__contains=q) | Q(content__contains=q))
            return object_list
        except Exception as e:
            self.request.session['search_error'] = "An error occurred while searching. Please try right term again"
            return Post.objects.none()

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
    fields = ['content', 'rating']


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
