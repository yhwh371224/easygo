from django.db import models


class RequestLog(models.Model):
    region = models.ForeignKey("regions.Region", null=True, on_delete=models.SET_NULL)
    path = models.CharField(max_length=255)
    ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
