from django.db import models

class WorkScheduleChoices(models.TextChoices):
    FULL_TIME = 'Full time'
    PART_TIME = 'Part time'
    HYBRID = 'Hybrid'

class Vacancy(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    address = models.CharField(max_length=50)
    work_schedule = models.TextField(choices=WorkScheduleChoices.choices)
    deadline = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
