from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    # Получение активных вопросов для отзывов
    path('questions/', views.get_questions, name='get_questions'),
    
    # Создание отзыва с вопросом
    path('question-feedback/', views.create_question_feedback, name='create_question_feedback'),
    
    # Создание отзыва-рецензии
    path('review-feedback/', views.create_review_feedback, name='create_review_feedback'),
    
    # Получение одобренных отзывов для публичного отображения
    path('approved/', views.get_approved_feedback, name='get_approved_feedback'),
]
