from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from backend.models import User
from backend.tasks import send_email_task

# Создаем сам сигнал
new_order_signal = Signal()

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Отправка письма при сбросе пароля через Celery
    """
    # Вызываем фоновую задачу
    send_email_task.delay(
        subject=f"Password Reset Token for {reset_password_token.user}",
        message=reset_password_token.key,
        to_email=reset_password_token.user.email
    )

@receiver(new_order_signal)
def new_order_notification(user_id, **kwargs):
    """
    Отправка письма при создании заказа через Celery
    """
    user = User.objects.get(id=user_id)
    # Вызываем фоновую задачу
    send_email_task.delay(
        subject="Обновление статуса заказа",
        message="Заказ оформлен",
        to_email=user.email
    )