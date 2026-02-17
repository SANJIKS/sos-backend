import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field


class NewsCategory(models.Model):
    """Категории новостей"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=100, verbose_name=_('Название'))
    name_kg = models.CharField(max_length=100, blank=True, verbose_name=_('Название (КГ)'))
    name_en = models.CharField(max_length=100, blank=True, verbose_name=_('Название (EN)'))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_('Slug'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    description_kg = models.TextField(blank=True, verbose_name=_('Описание (КГ)'))
    description_en = models.TextField(blank=True, verbose_name=_('Описание (EN)'))
    color = models.CharField(max_length=7, default='#007bff', verbose_name=_('Цвет'))
    icon = models.CharField(max_length=50, blank=True, verbose_name=_('Иконка'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активна'))
    sort_order = models.IntegerField(default=0, verbose_name=_('Порядок сортировки'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        verbose_name = _('Категория новостей')
        verbose_name_plural = _('Категории новостей')
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['sort_order']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('news:category', kwargs={'slug': self.slug})

    def get_name_by_language(self, language_code):
        """Получить название на определенном языке"""
        if language_code == 'kg' and self.name_kg:
            return self.name_kg
        elif language_code == 'en' and self.name_en:
            return self.name_en
        return self.name

    def get_description_by_language(self, language_code):
        """Получить описание на определенном языке"""
        if language_code == 'kg' and self.description_kg:
            return self.description_kg
        elif language_code == 'en' and self.description_en:
            return self.description_en
        return self.description


class NewsTag(models.Model):
    """Теги для новостей"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Название'))
    name_kg = models.CharField(max_length=50, blank=True, verbose_name=_('Название (КГ)'))
    name_en = models.CharField(max_length=50, blank=True, verbose_name=_('Название (EN)'))
    slug = models.SlugField(max_length=50, unique=True, verbose_name=_('Slug'))
    color = models.CharField(max_length=7, default='#6c757d', verbose_name=_('Цвет'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))

    class Meta:
        verbose_name = _('Тег новостей')
        verbose_name_plural = _('Теги новостей')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('news:tag', kwargs={'slug': self.slug})

    def get_name_by_language(self, language_code):
        """Получить название на определенном языке"""
        if language_code == 'kg' and self.name_kg:
            return self.name_kg
        elif language_code == 'en' and self.name_en:
            return self.name_en
        return self.name


class News(models.Model):
    """Модель новостей"""
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        PUBLISHED = 'published', _('Опубликовано')
        ARCHIVED = 'archived', _('Архив')
        SCHEDULED = 'scheduled', _('Запланировано')

    class ContentType(models.TextChoices):
        NEWS = 'news', _('Новость')
        ARTICLE = 'article', _('Статья')
        STORY = 'story', _('История')
        ANNOUNCEMENT = 'announcement', _('Объявление')
        SUCCESS_STORY = 'success_story', _('История успеха')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    
    # Основная информация
    title = models.CharField(max_length=255, verbose_name=_('Заголовок'))
    title_kg = models.CharField(max_length=255, blank=True, verbose_name=_('Заголовок (КГ)'))
    title_en = models.CharField(max_length=255, blank=True, verbose_name=_('Заголовок (EN)'))
    
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_('Slug'))
    
    # Контент
    content = CKEditor5Field(verbose_name=_('Содержание'), config_name='extends')
    content_kg = CKEditor5Field(blank=True, verbose_name=_('Содержание (КГ)'), config_name='extends')
    content_en = CKEditor5Field(blank=True, verbose_name=_('Содержание (EN)'), config_name='extends')
    
    excerpt = models.TextField(blank=True, verbose_name=_('Краткое описание'))
    excerpt_kg = models.TextField(blank=True, verbose_name=_('Краткое описание (КГ)'))
    excerpt_en = models.TextField(blank=True, verbose_name=_('Краткое описание (EN)'))
    
    # Метаданные
    meta_title = models.CharField(max_length=255, blank=True, verbose_name=_('Meta Title'))
    meta_description = models.TextField(blank=True, verbose_name=_('Meta Description'))
    meta_keywords = models.CharField(max_length=255, blank=True, verbose_name=_('Meta Keywords'))

    # Классификация
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='news',
        verbose_name=_('Категория')
    )
    tags = models.ManyToManyField(
        NewsTag,
        blank=True,
        related_name='news',
        verbose_name=_('Теги')
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.NEWS,
        verbose_name=_('Тип контента')
    )
    
    # Статус и публикация
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Статус')
    )
    is_featured = models.BooleanField(default=False, verbose_name=_('Рекомендуемая'))
    is_pinned = models.BooleanField(default=False, verbose_name=_('Закрепленная'))
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Дата публикации')
    )
    scheduled_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Запланировано на')
    )
    
    # Автор и статистика
    author = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_news',
        verbose_name=_('Автор')
    )
    views_count = models.PositiveIntegerField(default=0, verbose_name=_('Количество просмотров'))
    likes_count = models.PositiveIntegerField(default=0, verbose_name=_('Количество лайков'))
    
    # SEO и социальные сети
    social_title = models.CharField(max_length=255, blank=True, verbose_name=_('Заголовок для соцсетей'))
    social_description = models.TextField(blank=True, verbose_name=_('Описание для соцсетей'))
    social_image = models.ImageField(
        upload_to='news/social/',
        blank=True,
        null=True,
        verbose_name=_('Изображение для соцсетей')
    )
    
    # Дополнительные поля
    external_url = models.URLField(blank=True, verbose_name=_('Внешняя ссылка'))
    video_url = models.URLField(blank=True, verbose_name=_('Ссылка на видео'))
    attachment = models.FileField(
        upload_to='news/attachments/',
        blank=True,
        null=True,
        verbose_name=_('Вложение')
    )

    class Meta:
        verbose_name = _('Новость')
        verbose_name_plural = _('Новости')
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['published_at']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['category']),
            models.Index(fields=['content_type']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Автоматически генерируем slug если не указан
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Если статус "опубликовано" и нет даты публикации, устанавливаем текущую
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('news:detail', kwargs={'slug': self.slug})

    def get_title_by_language(self, language_code):
        """Получить заголовок на определенном языке"""
        if language_code == 'kg' and self.title_kg:
            return self.title_kg
        elif language_code == 'en' and self.title_en:
            return self.title_en
        return self.title

    def get_content_by_language(self, language_code):
        """Получить содержание на определенном языке"""
        if language_code == 'kg' and self.content_kg:
            return self.content_kg
        elif language_code == 'en' and self.content_en:
            return self.content_en
        return self.content

    def get_excerpt_by_language(self, language_code):
        """Получить краткое описание на определенном языке"""
        if language_code == 'kg' and self.excerpt_kg:
            return self.excerpt_kg
        elif language_code == 'en' and self.excerpt_en:
            return self.excerpt_en
        return self.excerpt

    def increment_views(self):
        """Увеличить счетчик просмотров"""
        self.views_count += 1
        self.save(update_fields=['views_count'])

    def increment_likes(self):
        """Увеличить счетчик лайков"""
        self.likes_count += 1
        self.save(update_fields=['likes_count'])

    @property
    def is_published(self):
        """Проверить, опубликована ли новость"""
        return (
            self.status == self.Status.PUBLISHED and
            self.published_at and
            self.published_at <= timezone.now()
        )

    @property
    def reading_time(self):
        """Примерное время чтения (в минутах)"""
        word_count = len(self.content.split())
        return max(1, word_count // 200)

    @property
    def featured_image(self):
        """
        Возвращает главное изображение из галереи.
        Сначала ищет изображение, помеченное как is_main,
        если такого нет - возвращает первое изображение в галерее.
        """
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image

        first_image = self.images.first()
        if first_image:
            return first_image.image

        return None


class NewsImage(models.Model):
    """Галерея изображений для одной новости"""
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Новость')
    )
    image = models.ImageField(
        upload_to='news/gallery/',
        verbose_name=_('Изображение')
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Подпись')
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name=_('Сделать главным?')
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата загрузки')
    )

    class Meta:
        verbose_name = _('Изображение новости')
        verbose_name_plural = _('Изображения новостей')
        ordering = ['-is_main', 'uploaded_at']

    def __str__(self):
        return f"Изображение для: {self.news.title}"
