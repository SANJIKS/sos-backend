from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.programs.validators import validate_image_or_svg_file
from apps.common.mixins import BaseModel


class SocialNetwork(BaseModel):
    """
    Модель для социальных сетей
    """
    class NetworkType(models.TextChoices):
        FACEBOOK = 'facebook', _('Facebook')
        INSTAGRAM = 'instagram', _('Instagram')
        YOUTUBE = 'youtube', _('YouTube')
        LINKEDIN = 'linkedin', _('LinkedIn')
        TWITTER = 'twitter', _('Twitter')
        TELEGRAM = 'telegram', _('Telegram')
        VKONTAKTE = 'vkontakte', _('ВКонтакте')
        TIKTOK = 'tiktok', _('TikTok')
        OTHER = 'other', _('Другое')

    name = models.CharField(max_length=100, verbose_name=_('Название'))
    network_type = models.CharField(
        max_length=20,
        choices=NetworkType.choices,
        verbose_name=_('Тип социальной сети')
    )
    url = models.URLField(verbose_name=_('Ссылка'))
    
    # Иконка
    icon = models.CharField(
        max_length=50, 
        verbose_name=_('Иконка'),
        help_text=_('Название иконки для отображения (например: facebook, instagram)')
    )
    custom_icon = models.FileField(
        upload_to='social_networks/icons/', 
        blank=True, 
        null=True, 
        validators=[validate_image_or_svg_file],
        verbose_name=_('Пользовательская иконка')
    )
    
    # Управление отображением
    is_active = models.BooleanField(default=True, verbose_name=_('Активна'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Рекомендуемая'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок отображения'))
    
    # Дополнительная информация
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    followers_count = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Количество подписчиков'))
    is_verified = models.BooleanField(default=False, verbose_name=_('Верифицированная'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

    class Meta:
        verbose_name = _('Социальная сеть')
        verbose_name_plural = _('Социальные сети')
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} - {self.get_network_type_display()}"
