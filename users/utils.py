# users/utils.py

from .models import *
from django.core.mail import send_mail
from django.conf import settings

def log_user_action(user, action_name, description, status='Успешно'):
    """
    Функция для записи действий пользователей в системе в таблицу User_action.
    """
    try:
        action_type = Action_type.objects.get(name=action_name)
    except Action_type.DoesNotExist:
        action_type = Action_type.objects.create(name=action_name)
    
    User_action.objects.create(
        type=action_type,
        user=user,
        description=description,
        status=status
    )

def send_mail_notification(users, header, text):
    """
    Функция для отправки сообщения на почту указанных пользователей.
    """
    for user in users:
        if user.notifications_status:
            send_mail(
                header,
                text,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
