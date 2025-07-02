# management/signals.py

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Group

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    default_groups = [
        "Исполнитель",
        "Менеджер",
        "Руководитель проекта"
    ]

    for group in default_groups:
        Group.objects.get_or_create(name=group)
