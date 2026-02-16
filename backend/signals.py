from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from backend.models import ConfirmEmailToken, User

# Создаем сам сигнал
new_order_signal = Signal()

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Отправка письма при сбросе пароля
    """
    msg = EmailMultiAlternatives(
        f"Password Reset Token for {reset_password_token.user}",
        reset_password_token.key,
        settings.EMAIL_HOST_USER,
        [reset_password_token.user.email]
    )
    msg.send()

@receiver(new_order_signal)
def new_order_notification(user_id, **kwargs):
    """
    Отправка письма при создании заказа
    """
    user = User.objects.get(id=user_id)
    msg = EmailMultiAlternatives(
        f"Обновление статуса заказа",
        'Заказ оформлен',
        settings.EMAIL_HOST_USER,
        [user.email]
    )
    msg.send()