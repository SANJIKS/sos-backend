from django.db import models
from django.utils.translation import gettext_lazy as _


class KeyEvent(models.Model):
    year = models.DateField()
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='key_events/', blank=True)