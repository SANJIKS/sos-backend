from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from apps.common.mixins import BaseContentModel, BaseModel
from .validators import validate_image_or_svg_file
import re


def create_slug(text):
    """
    Создает slug из текста с поддержкой кириллицы
    """
    # Словарь для транслитерации кириллицы
    translit_dict = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    
    # Транслитерация
    for cyr, lat in translit_dict.items():
        text = text.replace(cyr, lat)
    
    # Применяем стандартный slugify
    return slugify(text)


class Program(BaseContentModel):
    """
    Модель для программ/направлений деятельности
    """
    class ProgramType(models.TextChoices):
        DEINSTITUTIONALIZATION = 'deinstitutionalization', _('Программы деинституционализации')
        CHILD_PROTECTION = 'child_protection', _('Реформы систем защиты прав детей')
        GRADUATE_SUPPORT = 'graduate_support', _('Профессиональная подготовка и поддержка выпускников')
        ALTERNATIVE_CARE = 'alternative_care', _('Альтернативный уход')
        PREVENTION = 'prevention', _('Превенция')
        ADVOCACY = 'advocacy', _('Адвокация')
        HUMANITARIAN_AID = 'humanitarian_aid', _('Гуманитарная помощь')
        MENTAL_HEALTH = 'mental_health', _('Психическое здоровье')
        
        # Направления деятельности "Что мы делаем"
        CHILDREN_VILLAGES = 'children_villages', _('SOS Детские деревни')
        CRISIS_HOMES = 'crisis_homes', _('Кризисные и переходные дома')
        FAMILY_STRENGTHENING = 'family_strengthening', _('Программа укрепления семьи')
        GRADUATE_SUPPORT_DIRECTION = 'graduate_support_direction', _('Поддержка выпускников')
        SOS_PARENTS_TRAINING = 'sos_parents_training', _('Подготовка SOS-родителей')
        PSYCHOLOGICAL_SUPPORT = 'psychological_support', _('Психологическая и социальная помощь')
        
        OTHER = 'other', _('Другое')

    short_description = models.TextField(max_length=300, verbose_name=_('Краткое описание'))
    program_type = models.CharField(
        max_length=30,
        choices=ProgramType.choices,
        verbose_name=_('Тип программы')
    )
    
    # Изображения и медиа
    icon = models.FileField(
        upload_to='programs/icons/', 
        blank=True, 
        null=True, 
        validators=[validate_image_or_svg_file],
        verbose_name=_('Иконка')
    )
    main_image = models.ImageField(upload_to='programs/images/', blank=True, null=True, verbose_name=_('Главное изображение'))
    video_url = models.URLField(blank=True, null=True, verbose_name=_('Ссылка на видео'))
    video_thumbnail = models.ImageField(upload_to='programs/video_thumbnails/', blank=True, null=True, verbose_name=_('Превью видео'))
    
    # Дополнительные флаги
    is_main_program = models.BooleanField(default=False, verbose_name=_('Основная программа'))
    
    # Дополнительная информация
    content = models.TextField(blank=True, verbose_name=_('Подробное содержание'))
    target_audience = models.CharField(max_length=200, blank=True, verbose_name=_('Целевая аудитория'))
    duration = models.CharField(max_length=100, blank=True, verbose_name=_('Продолжительность'))
    
    # Автор видео/контента
    author_name = models.CharField(max_length=200, blank=True, verbose_name=_('Имя автора'))
    author_title = models.CharField(max_length=200, blank=True, verbose_name=_('Должность автора'))
    
    # Цитата
    quote = models.TextField(blank=True, verbose_name=_('Цитата'))

    class Meta:
        verbose_name = _('Программа')
        verbose_name_plural = _('Программы')
        ordering = ['order', 'title']

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = create_slug(self.title)
        super().save(*args, **kwargs)


class ProgramStep(BaseModel):
    """
    Модель для этапов работы программы
    """
    program = models.ForeignKey(
        Program, 
        on_delete=models.CASCADE, 
        related_name='steps',
        verbose_name=_('Программа')
    )
    title = models.CharField(max_length=200, verbose_name=_('Название этапа'))
    description = models.TextField(verbose_name=_('Описание этапа'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок'))
    icon = models.FileField(
        upload_to='programs/steps/icons/', 
        blank=True, 
        null=True, 
        validators=[validate_image_or_svg_file],
        verbose_name=_('Иконка этапа')
    )
    
    class Meta:
        verbose_name = _('Этап программы')
        verbose_name_plural = _('Этапы программ')
        ordering = ['order']
    
    def __str__(self):
        return f"{self.program.title} - {self.title}"
