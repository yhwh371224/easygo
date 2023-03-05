from django.shortcuts import render, redirect
from .models import Post
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from basecamp.area import suburbs


class PostList(ListView):
    model = Post

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)

        return context


class PostSearch(PostList):
    def get_queryset(self):
        q = self.kwargs['q']
        object_list = Post.objects.filter(
            Q(flight_date__contains=q) | Q(name__contains=q) | Q(contact__contains=q)
            | Q(suburb__contains=q) | Q(email__contains=q))

        return object_list

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostSearch, self).get_context_data()
        context['search_info'] = 'Search: "{}"'.format(self.kwargs['q'])
        return context


class PostDetail(DetailView):
    model = Post

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PostDetail, self).get_context_data(**kwargs)

        return context


class PostCreate(CreateView):
    model = Post
    fields = [
        'name', 'contact', 'email', 'street', 'suburb', 'flight_date',
        'direction', 'flight_number', 'flight_time', 'pickup_time',
        'no_of_passenger', 'no_of_baggage', 'message',
    ]

    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated:
            form.instance.author = current_user
            return super(type(self), self).form_valid(form)
        else:
            return redirect('/home/')


class PostUpdate(UpdateView):
    model = Post
    fields = [
        'name', 'contact', 'email', 'street', 'suburb', 'flight_date',
        'direction', 'flight_number', 'flight_time', 'pickup_time',
        'no_of_passenger','no_of_baggage', 'message',
    ]


