# projects/serializers.py

from management.models import Group, User_project
from rest_framework import serializers
from django.utils.timezone import now
from users.utils import *
from .models import *


# Сериализатор для создания проекта
class CreateProjectSerializer(serializers.ModelSerializer):
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        write_only=True,
        error_messages={'does_not_exist': 'Пользователь не найден, операция невозможна.'}
    )

    class Meta:
        model = Project
        fields = ['title', 'description', 'due_date', 'status', 'priority', 'is_gittable', 'git_url', 'created_by_id']

    def validate(self, data):
        user = data.get('created_by_id')

        if not user.is_project_leader:
            log_user_action(
                user=user, 
                action_name="Проекты", 
                description=f"Пользователь сделал запрос на создание проекта",
                status='Ошибка прав доступа'
                )
            raise serializers.ValidationError({'no_rights': 'У вас нет прав на создание проектов.'})
        
        due_date = data.get('due_date')

        if due_date and due_date < now().date():
            raise serializers.ValidationError({'due_date': 'Некорректная дата завершения проекта. Дата не должна быть в прошлом.'})

        return data
    
    def create(self, validated_data):
        created_by = validated_data.pop('created_by_id')
        project = Project.objects.create(created_by=created_by, **validated_data)

        try:
            project_leader_group = Group.objects.get(name="Руководитель проекта")
        except Group.DoesNotExist:
            raise serializers.ValidationError({'group_error': 'Группа "Руководитель проекта" не найдена.'})

        User_project.objects.create(
            project=project,
            user_group=project_leader_group,
            user=created_by
        )

        log_user_action(
            user=created_by, 
            action_name="Проекты", 
            description=f"Пользователь создал проект «{project.title}»"
        )
        
        return project


# Сериализатор для получения информации о проектах
class GetProjectSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_first_name = serializers.CharField(source='created_by.first_name', read_only=True)
    created_by_last_name = serializers.CharField(source='created_by.last_name', read_only=True)

    participants = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'title', 
            'due_date', 
            'created_by_username', 
            'created_by_first_name', 
            'created_by_last_name', 
            'priority', 
            'status', 
            'description', 
            'created_at', 
            'updated_at', 
            'is_gittable', 
            'git_url', 
            'created_by',
            'participants'
        ]
        
    def get_participants(self, obj):
        participants = obj.project_user.all()
        return [participant.user.username for participant in participants]


# Сериализатор для изменения статуса проекта
class ChangeProjectStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['status']

    def validate(self, data):
        request = self.context['request']
        project = self.instance

        if project.created_by.id != request.user.id:
            log_user_action(
                user=request.user, 
                action_name="Проекты", 
                description=f"Пользователь послал запрос на изменение статуса проекта «{project.title}»",
                status='Ошибка прав доступа'
            )
            raise serializers.ValidationError({'no_rights': 'Вы не являетесь создателем проекта.'})

        return data
    
    def update(self, instance, validated_data):
        if instance.status != validated_data.get('status', instance.status):    
            instance = super().update(instance, validated_data)

            log_user_action(
                user=self.context['request'].user, 
                action_name="Проекты", 
                description=f"Пользователь изменил статус проекта «{instance.title}»"
            )

            return instance


# Сериализатор для изменения информации о проекте
class ChangeProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['title', 'description', 'due_date', 'priority', 'is_gittable', 'git_url']

    def validate(self, data):
        request = self.context['request']
        project = self.instance

        if project.created_by.id != request.user.id:
            log_user_action(
                user=request.user, 
                action_name="Проекты", 
                description=f"Пользователь послал запрос на изменение проекта «{project.title}»",
                status='Ошибка прав доступа'
            )
            raise serializers.ValidationError({'no_rights': 'У вас нет прав на изменение проекта.'})

        due_date = data.get('due_date')

        if due_date and due_date < now().date():
            raise serializers.ValidationError({'due_date': 'Некорректная дата завершения проекта. Дата не должна быть в прошлом.'})
        
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
                action_name="Проекты", 
                description=f"Пользователь изменил проект «{instance.title}»"
            )

        return instance