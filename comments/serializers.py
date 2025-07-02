# comments/serializers.py

from management.models import User_project
from rest_framework import serializers
from tasks.models import Task
from users.utils import *
from .models import *


# Сериализатор для создания комментария    
class CreateCommentSerializer(serializers.ModelSerializer):
    task_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(),
        error_messages={'does_not_exist': 'Задача не найдена, операция невозможна.'}
    )

    class Meta:
        model = Comment
        fields = ['task_id', 'text']

    def validate(self, data):
        user = self.context['request'].user
        task = data.get('task_id')

        is_project_leader = User_project.objects.filter(
            project=task.project,
            user_id=user,
            user_group_id__name="Руководитель проекта"
        ).exists()

        if not (task.created_by == user or task.assigned_to == user or is_project_leader):
            log_user_action(
                user=user, 
                action_name="Комментарии", 
                description=f"Пользователь послал запрос на создание комментария к задаче «{task.title}»",
                status='Ошибка прав доступа'
            )
            raise serializers.ValidationError({'no_rights': 'Вам запрещено оставлять здесь комментарии.'})

        if not data.get('text'):
            raise serializers.ValidationError({'no_text': 'Текст комментария обязателен.'})

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        task = validated_data.pop('task_id')

        comment = super().create({**validated_data, 'created_by': user, 'task': task})

        log_user_action(
            user=user,
            action_name="Комментарии",
            description=f"Пользователь успешно создал комментарий к задаче «{task.title}»",
            status='Успешно'
        )

        receiver = task.assigned_to if task.created_by == user else task.created_by

        send_mail_notification(
            users=[receiver], 
            header="Получен новый комментарий", 
            text=f"К задаче «{task.title}» проекта «{task.project.title}» добавлен новый комментарий."
        )

        return comment
    

# Сериализатор для получения комментариев
class GetCommentSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_first_name = serializers.CharField(source='created_by.first_name', read_only=True)
    created_by_last_name = serializers.CharField(source='created_by.last_name', read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'task', 'text', 'created_at', 'is_edited',
            'created_by_username', 'created_by_first_name', 'created_by_last_name', 'created_by',
        ]


# Сериализатор для редактирования комментария
class UpdateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text']
    
    def validate(self, data):
        user = self.context['request'].user
        comment = self.instance

        if comment.created_by != user:
            log_user_action(
                user=user, 
                action_name="Комментарии", 
                description=f"Пользователь послал запрос на изменение коммментария к задаче «{comment.task.title}»",
                status='Ошибка прав доступа'
            )
            raise serializers.ValidationError({'no_rights': 'Вы не можете редактировать этот комментарий.'})

        if not data.get('text'):
            raise serializers.ValidationError({'no_text': 'Текст комментария обязателен.'})
        
        return data

    def update(self, instance, validated_data):
        text = validated_data.get('text')

        if instance.text != text:
            instance.text = text
            instance.is_edited = True

            instance.save()

            log_user_action(
                user=instance.created_by, 
                action_name="Комментарии", 
                description=f"Пользователь изменил комментарий к задаче «{instance.task.title}»"
            )

        return instance
