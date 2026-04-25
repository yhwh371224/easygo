from django.db import models


class Region(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    airport_code = models.CharField(max_length=10)
    timezone = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


REGION_DEFAULTS = [
    {
        'slug': 'melbourne',
        'name': 'Melbourne',
        'airport_code': 'MEL',
        'timezone': 'Australia/Melbourne',
        'phone': '03 9999 9999',
    },
    {
        'slug': 'brisbane',
        'name': 'Brisbane',
        'airport_code': 'BNE',
        'timezone': 'Australia/Brisbane',
        'phone': '07 9999 9999',
    },
    {
        'slug': 'adelaide',
        'name': 'Adelaide',
        'airport_code': 'ADL',
        'timezone': 'Australia/Adelaide',
        'phone': '08 9999 9999',
    },
    {
        'slug': 'perth',
        'name': 'Perth',
        'airport_code': 'PER',
        'timezone': 'Australia/Perth',
        'phone': '08 9999 9998',
    },
    {
        'slug': 'gold-coast',
        'name': 'Gold Coast',
        'airport_code': 'OOL',
        'timezone': 'Australia/Brisbane',
        'phone': '07 9999 9998',
    },
]
