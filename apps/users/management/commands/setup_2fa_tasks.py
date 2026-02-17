from django.core.management.base import BaseCommand
from apps.users.tasks import setup_periodic_tasks


class Command(BaseCommand):
    help = 'Настройка периодических задач для двухфакторной аутентификации'

    def handle(self, *args, **options):
        self.stdout.write('Настройка периодических задач 2FA...')
        
        try:
            tasks = setup_periodic_tasks()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Успешно настроены периодические задачи:\n'
                    f'  - Очистка истекших кодов (каждые 10 минут)\n'
                    f'  - Очистка старых логов (каждый день)\n'
                    f'  - Проверка безопасности (каждый час)\n'
                    f'  - Напоминания админам (каждую неделю)'
                )
            )
            
            # Показываем статус задач
            for task_name, task in tasks.items():
                status = "✅ Включена" if task.enabled else "❌ Отключена"
                self.stdout.write(f'  {task.name}: {status}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка при настройке задач: {str(e)}')
            ) 