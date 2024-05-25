from .models import Comment, Post
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('name', 'content', 'rating')
        widgets = {
            'rating': forms.HiddenInput(),
            }


User = get_user_model()

# class CustomLoginForm(AuthenticationForm):
#     username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'autofocus': True}))


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email", widget=forms.EmailInput(attrs={'autofocus': True}))