from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'easygo_review'

urlpatterns = [
    path('', views.PostList.as_view(), name="easygo_review"),
    path('create/', views.PostCreate.as_view(), name="easygo_review/create"),
    path('custom_login/', views.custom_login_view, name='custom_login'),
    path('custom_logout/', views.custom_logout_view, name='custom_logout'),
    path('recaptcha-verify/', views.recaptcha_verify, name='recaptcha_verify'),
    path('search/<str:q>/', views.PostSearch.as_view(), name="post_search"),
    path('<int:pk>/', views.PostDetail.as_view(), name="easygo_review/<pk>"),
    path('<int:pk>/update/', views.PostUpdate.as_view(), name="easygo_review/<pk>/update/"),
    path('<int:pk>/new_comment/', views.new_comment, name='new_comment'),
    path('comment/<int:pk>/update/', views.CommentUpdate.as_view(), name='comment_update'),
    path('comment/<int:pk>/delete/', views.CommentDelete.as_view(), name='comment_delete'),

]
