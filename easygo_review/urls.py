from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'easygo_review'

urlpatterns = [
    path('', views.PostList.as_view(), name="easygo_review"),
    path('create/', views.PostCreate.as_view(), name="easygo_review_create"),
    path('custom_login/', views.custom_login_view, name='custom_login'),
    path('custom_logout/', views.custom_logout_view, name='custom_logout'),
    path('recaptcha-verify/', views.recaptcha_verify, name='recaptcha_verify'),
    path('search/<str:q>/', views.PostSearch.as_view(), name="post_search"),
    path('<int:pk>/', views.PostDetail.as_view(), name="post_detail"),
    path('<int:pk>/update/', views.PostUpdate.as_view(), name="post_update"),
    path('<int:pk>/new_comment/', views.CommentCreate.as_view(), name='new_comment'),
    path('comment/<int:pk>/update/', views.CommentUpdate.as_view(), name='comment_update'),
    path('comment/<int:pk>/delete/', views.CommentDelete.as_view(), name='comment_delete'),
    path('verse/', views.verse_input_view, name='verse_input'),
    path('verse_of_today/', views.verse_display_view, name='verse_display'),
]
