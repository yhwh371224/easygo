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
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('search/<str:q>/', views.PostSearch.as_view(), name="post_search"),
    path('<int:pk>/', views.PostDetail.as_view(), name="easygo_review/<pk>"),
    path('<int:pk>/update/', views.PostUpdate.as_view(), name="easygo_review/<pk>/update/"),
    path('<int:pk>/new_comment/', views.new_comment, name="easygo_review/<pk>/new_comment/"),
    path('edit_comment/<int:pk>/', views.CommentUpdate.as_view(), name='edit_comment'),
    path('delete_comment/<int:pk>/', views.delete_comment, name='delete_comment'),
]
