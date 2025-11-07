import json
import requests
import os

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.http import JsonResponse

from .models import Post, Comment
from .forms import CommentForm, PostForm
from blog.models import Post as BlogPost
from blog.tasks import send_notice_email
from main.settings import RECIPIENT_EMAIL
from .tasks import create_verse_image_task


def custom_login_view(request):
    error = None
    if request.method == 'POST':
        email = request.POST['email']
        posts = BlogPost.objects.filter(email=email)
        if posts.exists():
            post = posts.first()  
            request.session['email'] = post.email
            return redirect('easygo_review:easygo_review')
        else:
            error = 'This is not the email address used for booking'
    return render(request, 'easygo_review/custom_login.html', {'error': error})


def custom_logout_view(request):
    request.session.flush()    
    return redirect('easygo_review:easygo_review')


def get_authenticated_post(request):
    email = request.session.get('email')
    if email:
        posts = BlogPost.objects.filter(email=email)
        if posts.exists():
            return posts.first()  
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

        # send_notice_email.delay('reviews accessed', 'reviews accessed', RECIPIENT_EMAIL)

        authenticated_post = get_authenticated_post(self.request)
        context['authenticated_post'] = authenticated_post 

        email = self.request.session.get('email', None)
        if email:
            blog_post = BlogPost.objects.filter(email=email).first()  
            if blog_post:
                user_name = blog_post.name
                context['user_name'] = user_name
            else:
                context['user_name'] = None
        else:
            context['user_name'] = None

        context['email'] = email 
        context['search_error'] = self.request.session.get('search_error', None)  

        return context
    

class PostCreate(View):
    def get(self, request, *args, **kwargs):
        email = request.session.get('email')  
        if email:
            blog_post = BlogPost.objects.filter(email=email).first()
            form = PostForm(initial={'name': blog_post.name})  
        else:
            form = PostForm()
        return render(request, 'easygo_review/post_form.html', {'form': form, 'form_guide': 'Please post your review'})

    def post(self, request, *args, **kwargs):
        form = PostForm(request.POST)
        if form.is_valid():
            email = request.session.get('email')  
            if email:
                blog_post = BlogPost.objects.filter(email=email).first()
                form.instance.author = blog_post.name  
                form.instance.name = blog_post.name  
                rating = form.cleaned_data.get('rating')
                if not (1 <= rating <= 5):
                    form.add_error('rating', 'Rating must be between 1 and 5')
                    return render(request, 'easygo_review/post_form.html', {'form': form, 'form_guide': 'Please post your review'})
                form.save()

                send_notice_email.delay('sb created review', 'sb created review', RECIPIENT_EMAIL)

                return redirect('/easygo_review/')
        return render(request, 'easygo_review/post_form.html', {'form': form, 'form_guide': 'Please post your review'})
    

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
    template_name = 'easygo_review/post_detail1.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post_count'] = Post.objects.all().count()
        context['comment_form'] = CommentForm()

        email = self.request.session.get('email', None)
        context['email'] = email

        authenticated_post = get_authenticated_post(self.request)
        context['authenticated_post'] = authenticated_post 

        if email:
            blog_post = BlogPost.objects.filter(email=email).first()  
            if blog_post:
                user_name = blog_post.name
                context['user_name'] = user_name
            else:
                context['user_name'] = None
        else:
            context['user_name'] = None

        return context
        

class PostUpdate(UpdateView):
    model = Post
    template_name = 'easygo_review/post_form.html'
    fields = ['content', 'rating']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        email = self.request.session.get('email', None)
        context['email'] = email

        authenticated_post = get_authenticated_post(self.request)
        context['authenticated_post'] = authenticated_post 

        if email:
            blog_post = BlogPost.objects.filter(email=email).first()  
            if blog_post:
                user_name = blog_post.name
                context['user_name'] = user_name
            else:
                context['user_name'] = None
        else:
            context['user_name'] = None

        return context
    

class CommentCreate(View):
    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk)
        email = request.session.get('email', None)

        user_name = None
        if email:
            blog_post = BlogPost.objects.filter(email=email).first()
            if blog_post:
                user_name = blog_post.name

        comment_form = CommentForm()
        
        context = {
            'post': post,
            'email': email,
            'user_name': user_name,
            'comment_form': comment_form,
        }

        return render(request, 'easygo_review/post_detail1.html', context)

    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk)
        email = request.session.get('email', None)

        user_name = None
        if email:
            blog_post = BlogPost.objects.filter(email=email).first()
            if blog_post:
                user_name = blog_post.name

        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = user_name
            comment.email = email
            comment.save()
            return redirect(post.get_absolute_url())  # Redirect to post detail page

        # Render the form with errors if form is not valid
        context = {
            'post': post,
            'email': email,
            'user_name': user_name,
            'comment_form': comment_form,
        }
        return render(request, 'easygo_review/post_detail1.html', context)
    

class CommentUpdate(UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'easygo_review/comment_form.html'

    def get_object(self, queryset=None):
        comment = super().get_object(queryset)        
        session_email = self.request.session.get('email', None)

        if comment.email != session_email:
            raise PermissionDenied('No right to edit')

        return comment
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email'] = self.request.session.get('email', None)
        return context

    def get_success_url(self):
        post = self.get_object().post
        return post.get_absolute_url() + '#comment-list'


class CommentDelete(DeleteView):
    model = Comment
    template_name = 'easygo_review/comment_confirm_delete.html'

    def get_object(self, queryset=None):
        comment = super().get_object(queryset)        
        session_email = self.request.session.get('email', None)

        if comment.email != session_email:
            raise PermissionDenied('No right to delete Comment')

        return comment
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email'] = self.request.session.get('email', None)
        return context

    def get_success_url(self):
        post = self.get_object().post
        return post.get_absolute_url() + '#comment-list'
    

def index(request):
    posts = Post.objects.all()
    return render(request, 'easygo_review/index.html', {'posts': posts})


def verify_recaptcha(response, version='v2'):
    if version == 'v2':
        secret_key = settings.RECAPTCHA_V2_SECRET_KEY
    elif version == 'v3':
        secret_key = settings.RECAPTCHA_V3_SECRET_KEY
    else:
        return {'success': False, 'error-codes': ['invalid-version']}

    data = {
        'secret': secret_key,
        'response': response
    }
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    return r.json()


@csrf_exempt
def recaptcha_verify(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        recaptcha_token = data.get('recaptchaToken')
        
        if not recaptcha_token:
            return JsonResponse({'success': False, 'message': 'No reCAPTCHA token provided'})

        result = verify_recaptcha(recaptcha_token, version='v3')
        
        if result.get('success'):
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': result.get('error-codes', 'Invalid reCAPTCHA token')})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# ----------------------------
# Verse 입력 view
# ----------------------------
def verse_input_view(request):
    if request.method == 'POST':
        verse_text = request.POST.get('verse')
        uploaded_image = request.FILES.get('background_image')

        if verse_text:
            uploaded_image_path = None

            # 업로드 파일 임시 저장
            if uploaded_image:
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_upload')
                os.makedirs(temp_dir, exist_ok=True)
                uploaded_image_path = os.path.join(temp_dir, uploaded_image.name)
                with open(uploaded_image_path, 'wb') as f:
                    for chunk in uploaded_image.chunks():
                        f.write(chunk)

            # Celery 비동기 호출
            create_verse_image_task.delay(verse_text, uploaded_image_path)

            messages.success(
                request,
                "Verse image creation started! It may take a few seconds."
            )
            return redirect('easygo_review:verse_of_today')

    return render(request, 'easygo_review/verse.html')


# ----------------------------
# Verse 출력 view
# ----------------------------
def verse_display_view(request):
    base_dir = os.path.join(settings.MEDIA_ROOT, 'verse')
    base_url = settings.MEDIA_URL.rstrip('/') + '/verse'

    image_basename = None
    image_ext = None

    if os.path.exists(base_dir):
        # verse_로 시작하고 이미지 확장자를 가진 파일만 가져오기
        files = sorted(
            [f for f in os.listdir(base_dir) if f.startswith('verse_') and f.lower().endswith(('.webp', '.jpg', '.png'))],
            key=lambda x: os.path.getmtime(os.path.join(base_dir, x)),
            reverse=True
        )
        if files:
            image_file = files[0]  # 최신 파일
            image_basename, image_ext = os.path.splitext(image_file)  # 확장자 분리

    context = {
        'image_basename': image_basename,  # None이면 템플릿에서 기본 처리
        'image_ext': image_ext,            # 확장자를 템플릿에서 사용
        'verse_text': "",
        'media_url': base_url
    }

    return render(request, 'easygo_review/verse_of_today.html', context)
