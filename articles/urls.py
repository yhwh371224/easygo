from django.urls import path
from . import views

app_name = 'articles'

urlpatterns = [
    path('blog/',          views.post_list,   name='post_list'),
    path('blog/<slug:slug>/', views.post_detail, name='post_detail'),
]
