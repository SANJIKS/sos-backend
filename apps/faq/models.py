from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.mixins import BaseModel

class FAQ(BaseModel):
    # Основные поля (русский язык)
    question = models.CharField(max_length=255, verbose_name=_('Вопрос'))
    answer = models.TextField(verbose_name=_('Ответ'))
    
    # Локализованные поля
    question_kg = models.CharField(max_length=255, blank=True, verbose_name=_('Вопрос (КГ)'))
    answer_kg = models.TextField(blank=True, verbose_name=_('Ответ (КГ)'))
    question_en = models.CharField(max_length=255, blank=True, verbose_name=_('Вопрос (EN)'))
    answer_en = models.TextField(blank=True, verbose_name=_('Ответ (EN)'))
    
    # Порядок отображения
    number_of_questions = models.IntegerField(default=1, unique=True, verbose_name=_('Порядок'))

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = _('Часто задаваемый вопрос')
        verbose_name_plural = _('Часто задаваемые вопросы')
        ordering = ['number_of_questions']