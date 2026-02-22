import os
from celery import Celery

# Устанавливаем настройки Django по умолчанию для celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netology_pd_diplom.settings')

app = Celery('netology_pd_diplom')

# Используем строку с префиксом CELERY_ в settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим задачи (tasks.py) в приложениях
app.autodiscover_tasks()