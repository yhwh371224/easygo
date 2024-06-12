from django.shortcuts import render, redirect
from .models import Post, Comment
from .forms import CommentForm, PostForm
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.db.models import Q
from blog.tasks import send_notice_email
from main.settings import RECIPIENT_EMAIL
from blog.models import Post as BlogPost
from django.core.exceptions import PermissionDenied
from django.views import View 


def custom_login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        post = BlogPost.objects.filter(email=email).first()
        if post:
            request.session['post_id'] = post.id
            return redirect('easygo_review:easygo_review')
        else:
            return render(request, 'easygo_review/custom_login.html', {'error': 'Invalid email address'})
    return render(request, 'easygo_review/custom_login.html')


def custom_logout_view(request):
    request.session.flush()    
    return redirect('/')


def get_authenticated_post(request):
    post_id = request.session.get('post_id')
    if post_id:
        try:
            return BlogPost.objects.get(id=post_id)
        except BlogPost.DoesNotExist:
            return None
    return None


class PostList(ListView):
    model = Post
    template_name = 'easygo_review/post_list.html'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        context['post_count'] = Post.objects.all().count()

        for post in context['object_list']:
            if post.rating is None:
                post.rating = 5

        send_notice_email.delay('reviews accessed', 'reviews accessed', RECIPIENT_EMAIL)

        authenticated_post = get_authenticated_post(self.request)
        context['authenticated_post'] = authenticated_post 

        post_id = self.request.session.get('post_id')
        if post_id:            
            blog_post = BlogPost.objects.get(id=post_id)
            user_name = blog_post.name
            context['user_name'] = user_name            

        return context
    

class PostSearch(PostList):
    def get_queryset(self):
        q = self.kwargs['q']
        object_list = Post.objects.filter(Q(name__contains=q) | Q(content__contains=q)) 
        return object_list

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostSearch, self).get_context_data(object_list=object_list, **kwargs)  
        context['search_info'] = 'Search: "{}"'.format(self.kwargs['q'])
        return context


class PostDetail(DetailView):
    model = Post
    template_name = 'easygo_review/post_detail.html'

    def get_context_data(self, **kwargs):
        context = super(PostDetail, self).get_context_data(**kwargs)
        context['post_count'] = Post.objects.all().count()
        context['comment_form'] = CommentForm()
        return context


class PostCreate(View):
    def get(self, request, *args, **kwargs):
        post_id = request.session.get('post_id')  
        if post_id:
            blog_post = BlogPost.objects.get(id=post_id)
            form = PostForm(initial={'name': blog_post.name})  
        else:
            form = PostForm()
        return render(request, 'easygo_review/post_form.html', {'form': form, 'form_guide': 'Please post your review'})

    def post(self, request, *args, **kwargs):
        form = PostForm(request.POST)
        if form.is_valid():
            post_id = request.session.get('post_id')  
            if post_id:
                blog_post = BlogPost.objects.get(id=post_id)
                form.instance.author = blog_post.name  
                form.instance.name = blog_post.name  
                rating = form.cleaned_data.get('rating')
                if not (1 <= rating <= 5):
                    form.add_error('rating', 'Rating must be between 1 and 5')
                    return render(request, 'easygo_review/post_form.html', {'form': form, 'form_guide': 'Please post your review'})
                form.save()
                return redirect('/easygo_review/')
        return render(request, 'easygo_review/post_form.html', {'form': form, 'form_guide': 'Please post your review'})


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
    return redirect('/easygo_review/')  # 


class CommentUpdate(UpdateView):
    model = Comment
    form_class = CommentForm

    def get_object(self, queryset=None):
        comment = super(CommentUpdate, self).get_object()
        if comment.author != self.request.user:
            raise PermissionDenied('No right to edit')  
        return comment


def delete_comment(request, pk):
    comment = Comment.objects.get(pk=pk)
    post = comment.post
    if request.user == comment.author:
        comment.delete()
        return redirect(post.get_absolute_url() + '#comment-list')
    else:
        raise PermissionDenied('No right to delete') 


class CommentDelete(DeleteView):
    model = Comment

    def get_object(self, queryset=None):
        comment = super(CommentDelete, self).get_object()
        if comment.author != self.request.user:
            raise PermissionDenied('No right to delete Comment')
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
