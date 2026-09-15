from django.db import models


class SearchSurveyResponse(models.Model):
    """A tester's answers from the 'search for EasyGo on Google' feedback
    page (basecamp:search_survey) — used to check how findable the site is
    and collect first-impression feedback on the homepage."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    keyword = models.CharField(max_length=200)
    page = models.CharField(max_length=50)
    landed = models.CharField(max_length=100)
    landed_note = models.CharField(max_length=300, blank=True)
    liked = models.TextField(blank=True)
    improve = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.name} — {self.keyword} ({self.page})"
