# statistics/serializers.py

from rest_framework import serializers


# Сериализатор для данных о распределении задач проекта по статусам
class TaskStatusDistributionSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


# Сериализатор для данных о распределении задач проекта по приоритетам
class TaskPriorityDistributionSerializer(serializers.Serializer):
    priority = serializers.CharField()
    count = serializers.IntegerField()


# Сериализатор для данных о нагрузке пользователей проекта
class LoadedUsersSerializer(serializers.Serializer):
    username = serializers.CharField()
    task_count = serializers.IntegerField()