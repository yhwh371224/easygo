from .models import Comment, Post
from django import forms


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254)


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
    
    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['readonly'] = True
