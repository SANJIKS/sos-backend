from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.mixins import BaseContentModel


class SuccessStory(BaseContentModel):
    """
    Модель для историй успеха и цитат
    """
    class StoryType(models.TextChoices):
        SUCCESS = 'success', _('Успех')
        FAMILY = 'family', _('Семья')
        EDUCATION = 'education', _('Образование')
        PERSONAL_GROWTH = 'personal_growth', _('Личностный рост')
        COMMUNITY = 'community', _('Сообщество')
        OTHER = 'other', _('Другое')

    quote_text = models.TextField(verbose_name=_('Текст цитаты'))
    author_name = models.CharField(max_length=100, verbose_name=_('Имя автора'))
    author_position = models.CharField(max_length=200, verbose_name=_('Должность автора'))
    author_image = models.ImageField(
        upload_to='success_stories/', 
        blank=True, 
        null=True, 
        verbose_name=_('Фото автора')
    )
    
    # Тип истории для фильтрации
    story_type = models.CharField(
        max_length=20,
        choices=StoryType.choices,
        default=StoryType.SUCCESS,
        verbose_name=_('Тип истории')
    )
    
    # Дополнительная информация
    description = models.TextField(blank=True, verbose_name=_('Описание'))

    class Meta:
        verbose_name = _('История успеха')
        verbose_name_plural = _('Истории успеха')
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.author_name}"


