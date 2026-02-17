from django.db import models
from django.core.validators import MinLengthValidator
from django.utils import timezone
import uuid


class FeedbackQuestion(models.Model):
    """Вопросы для отзывов"""
    text = models.CharField(max_length=255, verbose_name="Текст вопроса")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    
    class Meta:
        verbose_name = "Вопрос для отзыва"
        verbose_name_plural = "Вопросы для отзывов"
        ordering = ['order', 'id']
    
    def __str__(self):
        return self.text


class Feedback(models.Model):
    """Основная модель отзывов"""
    FEEDBACK_TYPES = [
        ('question', 'Отзыв с вопросом'),
        ('review', 'Отзыв-рецензия'),
    ]
    
    # Основные поля
    feedback_type = models.CharField(
        max_length=20, 
        choices=FEEDBACK_TYPES, 
        verbose_name="Тип отзыва"
    )
    name = models.CharField(max_length=100, verbose_name="Имя")
    email = models.EmailField(verbose_name="Email")
    message = models.TextField(
        validators=[MinLengthValidator(44)], 
        verbose_name="Сообщение"
    )
    
    # Дополнительные поля для отзыва-рецензии
    last_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Фамилия"
    )
    photo = models.ImageField(
        upload_to='feedback/photos/', 
        blank=True, 
        null=True, 
        verbose_name="Фотография"
    )
    
    # Поля для отзыва с вопросом
    question = models.ForeignKey(
        FeedbackQuestion, 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True, 
        verbose_name="Вопрос"
    )
    
    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")
    is_anonymous = models.BooleanField(default=False, verbose_name="Анонимный")
    
    # Защита от спама
    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")
    anonymous_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        verbose_name="Анонимный ID"
    )
    
    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_feedback_type_display()}"
    
    def save(self, *args, **kwargs):
        # Проверяем, что для отзыва с вопросом выбран вопрос
        if self.feedback_type == 'question' and not self.question:
            raise ValueError("Для отзыва с вопросом необходимо выбрать вопрос")
        
        # Проверяем, что для отзыва-рецензии заполнена фамилия
        if self.feedback_type == 'review' and not self.last_name:
            raise ValueError("Для отзыва-рецензии необходимо указать фамилию")
        
        super().save(*args, **kwargs)


class FeedbackSpamProtection(models.Model):
    """Модель для дополнительной защиты от спама"""
    ip_address = models.GenericIPAddressField(unique=True, verbose_name="IP адрес")
    attempts_count = models.PositiveIntegerField(default=0, verbose_name="Количество попыток")
    last_attempt = models.DateTimeField(auto_now=True, verbose_name="Последняя попытка")
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокирован")
    blocked_until = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Заблокирован до"
    )
    
    class Meta:
        verbose_name = "Защита от спама"
        verbose_name_plural = "Защита от спама"
    
    def __str__(self):
        return f"{self.ip_address} - {self.attempts_count} попыток"
    
    def is_currently_blocked(self):
        """Проверяет, заблокирован ли IP в данный момент"""
        if not self.is_blocked:
            return False
        if self.blocked_until and timezone.now() > self.blocked_until:
            self.is_blocked = False
            self.blocked_until = None
            self.save()
            return False
        return True
