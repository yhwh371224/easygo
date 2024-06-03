from django.urls import path
from . import views


urlpatterns = [
    path('search/<str:q>/', views.PostSearch.as_view()),
    path('edit_comment/<int:pk>/', views.CommentUpdate.as_view()),
    path('delete_comment/<int:pk>/', views.delete_comment),
    path('<int:pk>/new_comment/', views.new_comment, name="easygo_review/<pk>/new_comment/"),
    path('<int:pk>/update/', views.PostUpdate.as_view(), name="easygo_review/<pk>/update/"),
    path('<int:pk>/', views.PostDetail.as_view(), name="easygo_review/<pk>"),
    path('create/', views.PostCreate.as_view(), name="easygo_review/create"),
    path('', views.PostList.as_view(), name="easygo_review"),

]

