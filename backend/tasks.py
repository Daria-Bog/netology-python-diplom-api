from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

@shared_task
def send_email_task(subject, message, to_email):
    msg = EmailMultiAlternatives(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email]
    )
    msg.send()