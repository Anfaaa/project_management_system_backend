# users/signals.py

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Action_type

@receiver(post_migrate)
def create_default_action_types(sender, **kwargs):
    default_actions = [
        "Вступление в проекты",
        "Управление пользователями",
        "Проекты",
        "Комментарии",
        "Задачи",
        "Аккаунты"
    ]

    for action in default_actions:
        Action_type.objects.get_or_create(name=action)