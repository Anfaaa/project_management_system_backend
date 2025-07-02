# tasks/serializers.py

from management.models import User_project
from rest_framework import serializers
from django.utils.timezone import now
from users.utils import *
from .models import *


# Сериализатор для создания задачи
class CreateTaskSerializer(serializers.ModelSerializer):
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        write_only=True,
        error_messages={'does_not_exist': 'Пользователь не найден, операция невозможна.'}
    )
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        error_messages={'does_not_exist': 'Пользователь не найден, операция невозможна.'}
    )
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        error_messages={'does_not_exist': 'Проект не найден, операция невозможна.'}
    )

    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'status', 'priority', 'is_gittable', 'git_url', 
                  'project_id', 'assigned_to_id', 'created_by_id']

    def validate(self, data):
        user = data.get('created_by_id')
        assigned_to = data.get('assigned_to_id')
        project = data.get('project_id')

        if user.is_admin:
            raise serializers.ValidationError({'no_rights': 'У администраторов нет прав на создание задач.'})
        
        due_date = data.get('due_date')

        if due_date and due_date < now().date():
            raise serializers.ValidationError({'due_date': 'Некорректная дата сдачи задания. Дата не должна быть в прошлом.'})
        
        user_project_group = User_project.objects.filter(
            user=user,
            project=project
        ).first()

        if not user_project_group:
            log_user_action(
                user=user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на добавление задачи в проект «{project.title}»",
                status='Ошибка прав доступа к проекту'
            )
            raise serializers.ValidationError({'no_membership': 'Вы не участвуете в этом проекте.'})

        user_group_name = user_project_group.user_group.name
        can_not_assign_to_others = user_group_name == 'Исполнитель'

        if can_not_assign_to_others and assigned_to and assigned_to != user:
            log_user_action(
                user=user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на добавление задачи в проект «{project.title}»",
                status='Ошибка прав назначения задач'
            )
            raise serializers.ValidationError({
                'no_assign_rights': 'У вас нет прав назначать задачи другим пользователям.'
            })

        return data
    
    def create(self, validated_data):
        validated_data['project'] = validated_data.pop('project_id')
        validated_data['assigned_to'] = validated_data.pop('assigned_to_id')
        validated_data['created_by'] = validated_data.pop('created_by_id')
        
        task = super().create(validated_data)

        log_user_action(
            user=task.created_by,
            action_name="Задачи",
            description=f"Пользователь создал задачу «{task.title}»"
        )

        send_mail_notification(
            users=[task.assigned_to],
            header="Новая задача",
            text=f"Обнаружена новая порученная Вам задача «{task.title}» в проекте «{task.project.title}»."
        )

        return task


# Сериализатор для получения информации о задачах
class GetTaskSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_first_name = serializers.CharField(source='created_by.first_name', read_only=True)
    created_by_last_name = serializers.CharField(source='created_by.last_name', read_only=True)
    assigned_to_username = serializers.CharField(source='assigned_to.username', read_only=True)
    assigned_to_first_name = serializers.CharField(source='assigned_to.first_name', read_only=True)
    assigned_to_last_name = serializers.CharField(source='assigned_to.last_name', read_only=True)
    project_name = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'created_at', 'updated_at',
                  'due_date', 'status', 'priority',
                  'is_gittable', 'git_url', 'project_name', 'project',
                  'created_by', 'created_by_username', 
                  'created_by_first_name', 'created_by_last_name', 
                  'assigned_to','assigned_to_username', 
                  'assigned_to_first_name', 'assigned_to_last_name',
                ]


# Сериализатор для изменения статуса задачи
class ChangeTaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['status']

    def validate(self, data):
        request = self.context['request']
        task = self.instance

        if (task.created_by.id != request.user.id) and (task.assigned_to.id != request.user.id):
            log_user_action(
                user=request.user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на изменение статуса задачи «{task.title}»",
                status='Ошибка прав доступа'
            )
            raise serializers.ValidationError({'no_rights': 'Вы не имеете право на изменение статуса этой задачи.'})

        return data
    
    def update(self, instance, validated_data):
        if instance.status != validated_data.get('status', instance.status):
            instance = super().update(instance, validated_data)
            user = self.context['request'].user

            log_user_action(
                user=user, 
                action_name="Задачи", 
                description=f"Пользователь изменил статус задачи «{instance.title}»"
            )

            receiver = instance.assigned_to if instance.created_by == user else instance.created_by

            send_mail_notification(
                users=[receiver], 
                header="Изменение статуса в задаче", 
                text=f"Изменился статус задачи «{instance.title}» проекта «{instance.project.title}»."
            )

        return instance
    

# Сериализатор для изменения информации о задаче    
class ChangeTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'is_gittable', 'git_url', 'assigned_to']

    def validate(self, data):
        request = self.context['request']
        task = self.instance

        if task.created_by.id != request.user.id:
            log_user_action(
                user=request.user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на изменение задачи «{task.title}»",
                status='Ошибка прав доступа'
            )
            raise serializers.ValidationError({'no_rights': 'У вас нет прав на изменение этой задачи.'})

        due_date = data.get('due_date')

        if due_date and due_date < now().date():
            raise serializers.ValidationError({'due_date': 'Некорректная дата сдачи задания. Дата не должна быть в прошлом.'})

        return data
    
    def update(self, instance, validated_data):
        fields_changed = False

        for field in validated_data:
            if getattr(instance, field) != validated_data[field]:
                fields_changed = True
                break

        if fields_changed:
            instance = super().update(instance, validated_data)

            log_user_action(
                user=self.context['request'].user, 
                action_name="Задачи", 
                description=f"Пользователь изменил задачу «{instance.title}»"
            )
        
            send_mail_notification(
                users=[instance.assigned_to], 
                header="Изменения задачи", 
                text=f"Задача «{instance.title}» проекта «{instance.project.title}» была изменена."
            )

        return instance
