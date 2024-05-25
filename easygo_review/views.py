from django.shortcuts import render, redirect
from .models import Post, Comment
from .forms import CommentForm, PostForm
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from .forms import EmailLoginForm
from django.contrib.auth import authenticate, get_user_model


User = get_user_model()


class EmailLoginView(FormView):
    form_class = EmailLoginForm
    success_url = reverse_lazy('easygo_review')  # 로그인 성공 후 리디렉션할 URL
    template_name = 'easygo_review/login.html'

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = authenticate(self.request, username=email)
        if user is not None:
            login(self.request, user)
            return super().form_valid(form)
        else:
            form.add_error(None, 'No this email in our system')
            return self.form_invalid(form)


class PostList(ListView):
    model = Post
    template_name = 'easygo_review/post_list.html'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        context['post_count'] = Post.objects.all().count()
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
        if self.request.user.is_authenticated:
            current_user = self.request.user
            # current_user가 실제 User 인스턴스인지 확인
            if isinstance(current_user, get_user_model()):
                form.instance.author = current_user
                rating = form.cleaned_data.get('rating')
                if not (1 <= rating <= 5):
                    form.add_error('rating', 'Rating must be between 1 and 5')
                    return self.form_invalid(form)
                return super().form_valid(form)
            else:
                # current_user가 User 인스턴스가 아니면 리디렉션
                return redirect('/easygo_review/')
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
