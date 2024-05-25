from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView
from .views import EmailLoginView

app_name = 'easygo_review'
urlpatterns = [
    path('search/<str:q>/', views.PostSearch.as_view()),
    path('edit_comment/<int:pk>/', views.CommentUpdate.as_view()),
    path('delete_comment/<int:pk>/', views.delete_comment),
    path('<int:pk>/new_comment/', views.new_comment, name="easygo_review/<pk>/new_comment/"),
    path('<int:pk>/update/', views.PostUpdate.as_view(), name="easygo_review/<pk>/update/"),
    path('<int:pk>/', views.PostDetail.as_view(), name="easygo_review/<pk>"),
    path('create/', views.PostCreate.as_view(), name="easygo_review/create"),
    path('', views.PostList.as_view(), name="easygo_review"),
    path('login/', EmailLoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(next_page='easygo_review:easygo_review'), name='logout'),

]

