from django.urls import path
from . import views


urlpatterns = [
    path('search/<str:q>/', views.PostSearch.as_view()),
    path('<int:pk>/update/', views.PostUpdate.as_view(), name="blog/<pk>/update/"),
    path('<int:pk>/', views.PostDetail.as_view(), name="blog/<pk>"),
    path('create/', views.PostCreate.as_view(), name="blog/create"),
    path('', views.PostList.as_view(), name="blog"),

]

