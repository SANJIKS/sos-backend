from rest_framework import serializers
from .models import Feedback, FeedbackQuestion, FeedbackSpamProtection
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class FeedbackQuestionSerializer(serializers.ModelSerializer):
    """Сериализатор для вопросов отзывов"""
    
    class Meta:
        model = FeedbackQuestion
        fields = ['id', 'text', 'is_active', 'order']


class FeedbackQuestionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания отзыва с вопросом"""
    
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'question', 'message']
    
    def validate_message(self, value):
        """Проверяем минимальную длину сообщения"""
        if len(value) < 15:
            raise serializers.ValidationError(
                "Сообщение должно содержать минимум 15 символа"
            )
        return value
    
    def validate_question(self, value):
        """Проверяем, что вопрос активен"""
        if not value.is_active:
            raise serializers.ValidationError("Выбранный вопрос неактивен")
        return value


class FeedbackReviewCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания отзыва-рецензии"""
    
    class Meta:
        model = Feedback
        fields = ['name', 'last_name', 'email', 'message', 'photo']
    
    def validate_message(self, value):
        """Проверяем минимальную длину сообщения"""
        if len(value) < 15:
            raise serializers.ValidationError(
                "Сообщение должно содержать минимум 15 символа"
            )
        return value
    
    def validate_last_name(self, value):
        """Проверяем, что фамилия указана"""
        if not value:
            raise serializers.ValidationError("Фамилия обязательна для отзыва-рецензии")
        return value


class FeedbackListSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения отзывов"""
    question_text = serializers.CharField(source='question.text', read_only=True)
    feedback_type_display = serializers.CharField(source='get_feedback_type_display', read_only=True)
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'feedback_type', 'feedback_type_display', 'name', 'last_name', 
            'email', 'message', 'photo', 'question_text', 'created_at', 
            'is_approved', 'is_anonymous'
        ]
        read_only_fields = ['id', 'created_at']


class SpamProtectionMixin:
    """Миксин для защиты от спама"""
    
    def check_spam_protection(self, ip_address):
        """Проверяет защиту от спама для IP адреса"""
        from .models import Feedback
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # Проверяем, не отправлял ли этот IP отзыв сегодня
            today = timezone.now().date()
            today_feedback = Feedback.objects.filter(
                ip_address=ip_address,
                created_at__date=today
            ).exists()
            
            if today_feedback:
                raise serializers.ValidationError(
                    "Вы уже отправили отзыв сегодня"
                )
            
            spam_protection, created = FeedbackSpamProtection.objects.get_or_create(
                ip_address=ip_address
            )
            
            # Если IP заблокирован
            if spam_protection.is_currently_blocked():
                raise serializers.ValidationError(
                    "Ваш IP адрес временно заблокирован за подозрительную активность"
                )
            
            # Проверяем количество попыток за последний час
            one_hour_ago = timezone.now() - timedelta(hours=1)
            if spam_protection.last_attempt > one_hour_ago and spam_protection.attempts_count >= 5:
                # Блокируем IP на 24 часа
                spam_protection.is_blocked = True
                spam_protection.blocked_until = timezone.now() + timedelta(hours=24)
                spam_protection.save()
                raise serializers.ValidationError(
                    "Слишком много попыток отправки отзывов. Попробуйте позже."
                )
            
            # Увеличиваем счетчик попыток
            spam_protection.attempts_count += 1
            spam_protection.save()
            
        except Exception as e:
            if isinstance(e, serializers.ValidationError):
                raise e
            # В случае других ошибок не блокируем пользователя
            pass
