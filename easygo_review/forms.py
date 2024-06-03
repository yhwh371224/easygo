from .models import Comment, Post
from django import forms


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
