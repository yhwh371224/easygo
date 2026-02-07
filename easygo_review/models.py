from django.db import models
from django.contrib.auth.models import User
from markdownx.models import MarkdownxField
from markdownx.utils import markdown
import datetime


class Post(models.Model):
    content = MarkdownxField()
    name = models.CharField(max_length=100, blank=False, null=True)
    date = models.DateField(blank=True, null=True, default=datetime.date.today)
    link = models.URLField(max_length=100, default="https://www.google.com/search?q=EasyGo+Airport+Shuttle&ludocid=15709254108877640867#lrd=0x6b12a791a1292781:0xda027b617dff54a3,1")
    rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    is_published = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return str(self.author)

    def get_absolute_url(self):
        return '/easygo_review/{}/'.format(self.pk)

    def get_update_url(self):
        return self.get_absolute_url() + 'update/'

    def get_markdown_content(self):
        return markdown(self.content)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    text = MarkdownxField()
    author = models.CharField(max_length=100, blank=True, null=True) 
    email = models.EmailField(blank=True, null=True)   
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def get_markdown_content(self):
        return markdown(self.text)

    def get_absolute_url(self):
        return self.post.get_absolute_url() + '#comment-id-{}'.format(self.pk)

