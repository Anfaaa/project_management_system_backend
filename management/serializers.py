# management/serializers.py

from rest_framework import serializers
from projects.models import Project
from users.models import User
from users.utils import *
from .models import *


# Сериализатор для создания заявки на вступление в проект
class CreateProjectRequestSerializer(serializers.ModelSerializer):
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        error_messages={'does_not_exist': 'Проект не найден, операция невозможна.'}
    )

    class Meta:
        model = Project_request
        fields = ['project_id']

    def validate(self, data):
        user = self.context['request'].user
        project = data.get('project_id')

        if User_project.objects.filter(user=user, project=project).exists():
            raise serializers.ValidationError({'request_already_satisfied': 'Вы уже участвуете в этом проекте.'})
        
        if Project_request.objects.filter(created_by=user, project=project, status="Ожидает").exists():
            raise serializers.ValidationError({'request_already_exists': 'Вы уже подали заявку на вступление, '
            'она находится на рассмотрении. Ожидайте результатов. '
            'Ответ придет на указанную Вами почту, если уведомления разрешены.'})
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        project = validated_data['project_id']

        request_obj = Project_request.objects.create(
            project=project,
            created_by=user,
            status="Ожидает"
        )

        send_mail_notification(
            users=[project.created_by],
            header="Получена новая заявка на вступление в проект",
            text=f"Пользователь {user.username} подал заявку на вступление в проект «{project.title}»"
        )

        log_user_action(
            user=user,
            action_name="Вступление в проекты",
            description=f"Пользователь подал заявку в проект «{project.title}»"
        )

        return request_obj


# Сериализатор для получения списка участников проекта
class GetUsersSerializer(serializers.ModelSerializer):
    group_in_project = serializers.SerializerMethodField(read_only=True)
    date_joined_project = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'group_in_project', 'last_login', 'date_joined_project']

    def get_group_in_project(self, obj):
        project = self.context.get('project_id')  

        user_project = User_project.objects.filter(
            user=obj.id,
            project=project
        ).select_related('user_group').first()
        
        return user_project.user_group.name if user_project else None
    
    def get_date_joined_project(self, obj):
        project = self.context.get('project_id')
        user_project = User_project.objects.filter(
            user=obj.id,
            project=project
        ).first()
        return user_project.date_joined_project if user_project else None


# Сериализатор для получения заявок на вступление в проект
class GetProjectRequestsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='created_by.username')
    email = serializers.EmailField(source='created_by.email')
    first_name = serializers.CharField(source='created_by.first_name')
    last_name = serializers.CharField(source='created_by.last_name')

    class Meta:
        model = Project_request
        fields = ['id', 'created_by', 'username', 'email', 'first_name', 'last_name', 'status', 'created_at']


# Сериализатор для добавления пользователей в проект
class AddProjectMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    project_id = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    user_group = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Group.objects.all()
    )

    class Meta:
        model = User_project
        fields = ['user_id', 'project_id', 'user_group']

    def validate(self, data):
        user = data.get('user_id')
        project = data.get('project_id')
        requesting_user = self.context.get('request').user

        if project.created_by.id != requesting_user.id:
            log_user_action(
                user=requesting_user, 
                action_name="Вступление в проекты", 
                description=f"Пользователь послал запрос на добавление участника в проект «{project.title}»",
                status='Ошибка прав доступа'
            )
            raise serializers.ValidationError({"no_rights": "У Вас нет прав на добавление пользователей в проект."})

        request = Project_request.objects.filter(project=project, created_by=user).first()
        
        if request:
            request.status = "Принята"
            request.save()

        existing_membership = User_project.objects.filter(user=user, project=project).first()

        if existing_membership:
            raise serializers.ValidationError({"request_already_satisfied": "Пользователь уже состоит в проекте."})

        return data

    def create(self, validated_data):
        user_group = validated_data.get('user_group')
        user = validated_data.get('user_id')
        project = validated_data.get('project_id')
        requesting_user = self.context['request'].user

        member = User_project.objects.create(
            user=user,
            project=project,
            user_group=user_group
        )

        log_user_action(
            user=requesting_user, 
            action_name="Вступление в проекты", 
            description=f"Руководитель добавил {user.username} в проект «{project.title}»"
        )

        send_mail_notification(
            users=[user], 
            header="Вступление в проекты", 
            text=f"Вас добавили в проект «{project.title}»"
        )

        return member
    

# Сериализатор для изменения статуса заявки на вступление в проект
class SetProjectRequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_request
        fields = ['status']

    def validate(self, data):
        user = self.context['request'].user
        
        project_request = self.instance

        if project_request.status == "Отклонена":
            raise serializers.ValidationError({"request_already_satisfied":"Заявка уже отклонена."})

        if project_request.project.created_by != user:
            raise serializers.ValidationError({"no_rights": "У Вас нет прав для изменения статуса заявки."})

        return data
    
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        send_mail_notification(
            users=[instance.created_by], 
            header="Вступление в проекты", 
            text=f"Статус Вашей заявки на вступление в проект «{instance.project.title}» изменен на «{instance.status}»"
        )

        log_user_action(user=instance.project.created_by, 
            action_name="Управление пользователями", 
            description=f"Руководитель изменил статус заявки {instance.created_by} на «{instance.status}» в проекте «{instance.project.title}»"
        )

        return instance


# Сериализатор для получения названия группы пользователя в проекте
class UserProjectGroupSerializer(serializers.ModelSerializer):
    group_name_in_project = serializers.CharField(source='user_group.name', read_only=True)

    class Meta:
        model = User_project
        fields = ['group_name_in_project']


# Сериализатор для изменения группы пользователя в проекте
class UsersProjectsSerializer(serializers.ModelSerializer):

    class Meta:
        model = User_project
        fields = ['user', 'project', 'user_group']

    def update(self, instance, validated_data):
        user = self.context['request'].user
        executor_group = Group.objects.get(name="Исполнитель")
        manager_group = Group.objects.get(name="Менеджер")

        current_group = instance.user_group

        if current_group == executor_group:
            instance.user_group = manager_group  # Повышаем Исполнителя до Менеджера

        elif current_group == manager_group:
            instance.user_group = executor_group  # Понижаем Менеджера до Исполнителя

        else:
            raise serializers.ValidationError({'process_error':'Невозможно выполнить операцию, неверно указаны новые группы.'})
        
        instance.save()

        log_user_action(
            user=user, 
            action_name="Управление пользователями", 
            description=f"Руководитель изменил группу для {instance.user.username}"
        )
        
        send_mail_notification(
            users=[instance.user],
            header="Изменения группы",
            text=f"Ваша группа в проекте «{instance.project.title}» была изменена."
        )
        
        return instance 


# Сериализатор для изменения права руководителя проектов (права управления проектами)
class ChangeProjectLeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_project_leader']

    def update(self, instance, validated_data):
        user = self.context['request'].user

        instance.is_project_leader = not instance.is_project_leader
        instance.save()

        log_user_action(
            user=user, 
            action_name="Управление пользователями", 
            description=f"Администратор изменил право руководителя для {instance.username}"
        )

        send_mail_notification(
            users=[instance], 
            header="Изменение Ваших прав в системе", 
            text=f"Ваши права управления проектами были изменены."
        )

        return instance


# Сериализатор для блокировки/активации пользовательских аккаунтов
class ChangeActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']

    def update(self, instance, validated_data):
        user = self.context['request'].user

        instance.is_active = not instance.is_active
        instance.save()

        log_user_action(
            user=user, 
            action_name="Управление пользователями", 
            description=f"Администратор изменил доступ пользователю {instance.username} к аккаунту"
        )

        send_mail_notification(
            users=[instance], 
            header="Блокировка аккаунта", 
            text=f"Доступ к Вашему аккаунту был изменен."
        )

        return instance
