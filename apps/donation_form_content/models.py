from django.db import models

class DonationFormContent(models.Model):
    title = models.CharField(max_length=255)
    title_kg = models.CharField(max_length=255, blank=True)
    title_en = models.CharField(max_length=255, blank=True)
    
    description = models.TextField(blank=True)
    description_kg = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    
    button_text = models.CharField(max_length=100, default='Пожертвовать')
    button_text_kg = models.CharField(max_length=100, blank=True)
    button_text_en = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Контент формы донатов'
        verbose_name_plural = 'Контент формы донатов'

    def __str__(self):
        return self.title