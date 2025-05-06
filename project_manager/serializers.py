# serializers.py

from rest_framework import serializers
from .models import *
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils.timezone import now
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.conf import settings

def log_user_action(user, action_name, description, status='Успешно'):
    try:
        action_type = Action_types.objects.get(name=action_name)
    except Action_types.DoesNotExist:
        action_type = Action_types.objects.create(name=action_name)
    
    User_actions.objects.create(
        type_id=action_type,
        user_id=user,
        description=description,
        status=status
    )

def send_mail_notification(users, header, text):
    for user in users:
        if user.notifications_status:
            send_mail(
                header,
                text,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    username = serializers.CharField(
        validators=[UniqueValidator(queryset=Users.objects.all(), message="Этот логин уже занят.")]
    )
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=Users.objects.all(), message="Пользователь с таким email уже существует.")]
    )

    class Meta:
        model = Users
        fields = ('username', 'email', 'first_name', 'last_name', 'password')
    

    def create(self, validated_data):
        password = validated_data.pop('password')
        with transaction.atomic():
            user = Users(**validated_data)
            user.set_password(password)
            user.save()

            # Логирование действия
            log_user_action(
                user=user,
                action_name="Аккаунты",
                description=f"Пользователь создал аккаунт"
            )

        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        try:
            user = Users.objects.get(username=username)
        except Users.DoesNotExist:
            raise serializers.ValidationError({'username': 'Неверный логин или пароль.'})
        
        if not user.check_password(password):
            raise serializers.ValidationError({'password': 'Неверный логин или пароль.'})

        if not user.is_active:
            log_user_action(user=user, 
                        action_name="Аккаунты", 
                        description=f"Пользователь совершил попытку входа в систему",
                        status='Отказано в доступе')
            raise serializers.ValidationError({'blocked': 'Аккаунт временно заблокирован.'})
        
        user.last_login = now()
        user.save(update_fields=['last_login'])

        refresh_token = RefreshToken.for_user(user)

        log_user_action(user=user, 
                        action_name="Аккаунты", 
                        description=f"Пользователь вошел в систему")

        return {
            'refresh_token' : str(refresh_token),
            'access_token' : str(refresh_token.access_token),
            'user_id' : user.id,
            'username' : user.username,
            'email' : user.email,
            'is_admin' : user.is_admin,
            'is_project_leader' : user.is_project_leader,
            'notifications_status' : user.notifications_status,
            'theme_preference' : user.theme_preference,
            'git_account_enabled' : user.git_account_enabled,
        }
    

class CreateProjectSerializer(serializers.ModelSerializer):
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=Users.objects.all(), 
        write_only=True,
        error_messages={'does_not_exist': 'Пользователь не найден, операция невозможна.'}
    )

    class Meta:
        model = Projects
        fields = ['title', 'description', 'due_date', 'status', 'priority', 'is_gittable', 'git_url', 'created_by_id']

    def validate(self, data):
        user = data.get('created_by_id')

        if not user.is_project_leader:
            log_user_action(user=user, 
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
        project = Projects.objects.create(created_by_id=created_by, **validated_data)

        try:
            project_leader_group = Groups.objects.get(name="Руководитель проекта")
        except Groups.DoesNotExist:
            raise serializers.ValidationError({'group_error': 'Группа "Руководитель проекта" не найдена.'})

        Users_projects.objects.create(
            project_id=project,
            user_group_id=project_leader_group,
            user_id=created_by
        )
        log_user_action(user=created_by, 
                action_name="Проекты", 
                description=f"Пользователь создал проект «{project.title}»")
        return project

class GetProjectSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by_id.username', read_only=True)
    created_by_first_name = serializers.CharField(source='created_by_id.first_name', read_only=True)
    created_by_last_name = serializers.CharField(source='created_by_id.last_name', read_only=True)

    participants = serializers.SerializerMethodField()

    class Meta:
        model = Projects
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
            'created_by_id',
            'participants'
        ]
        
    def get_participants(self, obj):
        participants = obj.project_user.all()
        return [participant.user_id.username for participant in participants]


class ChangeProjectStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = ['status']

    def validate(self, data):
        request = self.context['request']
        project = self.instance

        if project.created_by_id.id != request.user.id:
            log_user_action(user=request.user, 
                action_name="Проекты", 
                description=f"Пользователь послал запрос на изменение статуса проекта «{project.title}»",
                status='Ошибка прав доступа')

            raise serializers.ValidationError({'no_rights': 'Вы не являетесь создателем проекта.'})
        
        log_user_action(user=request.user, 
            action_name="Проекты", 
            description=f"Пользователь изменил статус проекта «{project.title}»")

        return data
    
class ChangeProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = ['title', 'description', 'due_date', 'priority', 'is_gittable', 'git_url']

    def validate(self, data):
        request = self.context['request']
        project = self.instance

        if project.created_by_id.id != request.user.id:
            log_user_action(user=request.user, 
                action_name="Проекты", 
                description=f"Пользователь послал запрос на изменение проекта «{project.title}»",
                status='Ошибка прав доступа')
            raise serializers.ValidationError({'no_rights': 'У вас нет прав на изменение проекта.'})

        due_date = data.get('due_date')
        if due_date and due_date < now().date():
            raise serializers.ValidationError({'due_date': 'Некорректная дата завершения проекта. Дата не должна быть в прошлом.'})
        
        log_user_action(user=request.user, 
            action_name="Проекты", 
            description=f"Пользователь изменил проект «{project.title}»")
        
        return data
    
class CreateProjectRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_requests
        fields = ['project_id']

    def create(self, validated_data):
        user = self.context['request'].user
        project = validated_data['project_id']

        if Users_projects.objects.filter(user_id=user, project_id=project).exists():
            raise serializers.ValidationError({'request_already_satisfied': 'Вы уже участвуете в этом проекте.'})
        
        if Project_requests.objects.filter(created_by_id=user, project_id=project, status="Ожидает").exists():
            raise serializers.ValidationError({'request_already_exists': 'Вы уже подали заявку на вступление, она находится на рассмотрении. Ожидайте результатов.'})

        request_obj = Project_requests.objects.create(
            project_id=project,
            created_by_id=user,
            status="Ожидает"
        )

        send_mail_notification(
            users=[project.created_by_id],
            header="Получена новая заявка в проект",
            text=f"Пользователь {user.username} подал заявку на вступление в проект «{project.title}»"
        )

        log_user_action(
            user=user,
            action_name="Вступление в проекты",
            description=f"Пользователь подал заявку в проект «{project.title}»"
        )

        return request_obj

    
class GetUsersSerializer(serializers.ModelSerializer):
    group_in_project = serializers.SerializerMethodField(read_only=True)
    date_joined_project = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Users
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'group_in_project', 'last_login', 'date_joined_project']

    def get_group_in_project(self, obj):
        project_id = self.context.get('project_id')  

        user_project = Users_projects.objects.filter(
            user_id=obj.id,
            project_id=project_id
        ).select_related('user_group_id').first()
        
        return user_project.user_group_id.name if user_project else None
    
    def get_date_joined_project(self, obj):
        project_id = self.context.get('project_id')
        user_project = Users_projects.objects.filter(
            user_id=obj.id,
            project_id=project_id
        ).first()
        return user_project.date_joined_project if user_project else None

class GetProjectRequestsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='created_by_id.username')
    email = serializers.EmailField(source='created_by_id.email')
    first_name = serializers.CharField(source='created_by_id.first_name')
    last_name = serializers.CharField(source='created_by_id.last_name')

    class Meta:
        model = Project_requests
        fields = ['id', 'created_by_id', 'username', 'email', 'first_name', 'last_name', 'status', 'created_at']


class AddProjectMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=Users.objects.all())
    project_id = serializers.PrimaryKeyRelatedField(queryset=Projects.objects.all())
    user_group_id = serializers.CharField()

    class Meta:
        model = Users_projects
        fields = ['user_id', 'project_id', 'user_group_id']

    def validate(self, attrs):
        user = attrs.get('user_id')
        project = attrs.get('project_id')
        
        requesting_user = self.context.get('request').user
        if project.created_by_id.id != requesting_user.id:
            log_user_action(user=requesting_user, 
                action_name="Вступление в проекты", 
                description=f"Пользователь послал запрос на добавление участника в проект «{project.title}»",
                status='Ошибка прав доступа')
            raise serializers.ValidationError({"no_rights": "У Вас нет прав на добавление пользователей в проект."})

        request = Project_requests.objects.filter(project_id=project, created_by_id=user).first()
        if request:
            request.status = "Принята"
            request.save()

        existing_membership = Users_projects.objects.filter(user_id=user, project_id=project).first()
        if existing_membership:
            raise serializers.ValidationError({"request_already_satisfied": "Пользователь уже состоит в проекте."})

        return attrs

    def create(self, validated_data):
        user_group_name = validated_data.get('user_group_id')
        user = validated_data.get('user_id')
        project = validated_data.get('project_id')
        requesting_user = self.context.get('request').user

        user_group = Groups.objects.filter(name=user_group_name).first()
        if not user_group:
            raise serializers.ValidationError({"group_not_found": "Группа не найдена."})

        member = Users_projects.objects.create(
            user_id=user,
            project_id=project,
            user_group_id=user_group
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
    

class SetProjectRequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_requests
        fields = ['status']

    def validate(self, data):
        user = self.context['request'].user
        
        project_request = self.instance

        if project_request.status == "Отклонена":
            raise serializers.ValidationError({"request_already_satisfied":"Заявка уже отклонена."})

        if project_request.project_id.created_by_id != user:
            raise serializers.ValidationError({"no_rights": "У Вас нет прав для изменения статуса заявки."})

        send_mail_notification(
            users=[project_request.created_by_id], 
            header="Вступление в проекты", 
            text=f"Статус Вашей заявки на вступление в проект «{project_request.project_id.title}» изменен на «{project_request.status}»"
        )
        return data

class UserProjectGroupSerializer(serializers.ModelSerializer):
    group_name_in_project = serializers.CharField(source='user_group_id.name', read_only=True)

    class Meta:
        model = Users_projects
        fields = ['group_name_in_project']

class CreateTaskSerializer(serializers.ModelSerializer):
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=Users.objects.all(), 
        write_only=True,
        error_messages={'does_not_exist': 'Пользователь не найден, операция невозможна.'}
    )
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=Users.objects.all(),
        error_messages={'does_not_exist': 'Пользователь не найден, операция невозможна.'}
    )
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Projects.objects.all()
    )

    class Meta:
        model = Tasks
        fields = ['title', 'description', 'due_date', 'status', 'priority', 'is_gittable', 'git_url', 
                  'project_id', 'assigned_to_id', 'created_by_id']

    def validate(self, data):
        user = data.get('created_by_id')
        assigned_to = data.get('assigned_to_id')
        project = data.get('project_id')
        task_title = data.get('title')

        if user.is_admin:
            raise serializers.ValidationError({'no_rights': 'У администраторов нет прав на создание задач.'})
        
        due_date = data.get('due_date')
        if due_date and due_date < now().date():
            raise serializers.ValidationError({'due_date': 'Некорректная дата сдачи задания. Дата не должна быть в прошлом.'})
        
        user_project_group = Users_projects.objects.filter(
            user_id=user,
            project_id=project
        ).first()

        if not user_project_group:
            log_user_action(user=user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на добавление задачи в проект «{project.title}»",
                status='Ошибка прав доступа к проекту')
            raise serializers.ValidationError({'no_membership': 'Вы не участвуете в этом проекте.'})

        user_group_name = user_project_group.user_group_id.name
        can_not_assign_to_others = user_group_name == 'Исполнитель'

        if can_not_assign_to_others and assigned_to and assigned_to != user:
            log_user_action(user=user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на добавление задачи в проект «{project.title}»",
                status='Ошибка прав назначения задач')
            raise serializers.ValidationError({
                'no_assign_rights': 'У вас нет прав назначать задачи другим пользователям.'
            })
        
        log_user_action(user=user, 
            action_name="Задачи", 
            description=f"Пользователь создал задачу «{task_title}»")
        
        send_mail_notification(
            users=[assigned_to], 
            header="Новая задача", 
            text=f"Обнаружена новая порученная Вам задача «{task_title}» в проекте «{project.title}."
        )

        return data
    
class GetTaskSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by_id.username', read_only=True)
    created_by_first_name = serializers.CharField(source='created_by_id.first_name', read_only=True)
    created_by_last_name = serializers.CharField(source='created_by_id.last_name', read_only=True)
    assigned_to_username = serializers.CharField(source='assigned_to_id.username', read_only=True)
    assigned_to_first_name = serializers.CharField(source='assigned_to_id.first_name', read_only=True)
    assigned_to_last_name = serializers.CharField(source='assigned_to_id.last_name', read_only=True)
    project_name = serializers.CharField(source='project_id.title', read_only=True)

    class Meta:
        model = Tasks
        fields = ['id', 'title', 'description', 'created_at', 'updated_at',
                  'due_date', 'status', 'priority',
                  'is_gittable', 'git_url', 'project_name', 'project_id',
                  'created_by_id', 'created_by_username', 
                  'created_by_first_name', 'created_by_last_name', 
                  'assigned_to_id','assigned_to_username', 
                  'assigned_to_first_name', 'assigned_to_last_name',
                ]

class ChangeTaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tasks
        fields = ['status']

    def validate(self, data):
        request = self.context['request']
        task = self.instance
        if (task.created_by_id.id != request.user.id) and (task.assigned_to_id.id != request.user.id):
            log_user_action(user=request.user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на изменение статуса задачи «{task.title}»",
                status='Ошибка прав доступа')
            raise serializers.ValidationError({'no_rights': 'Вы не имеете право на изменение статуса этой задачи.'})

        log_user_action(user=request.user, 
            action_name="Задачи", 
            description=f"Пользователь изменил статус задачи «{task.title}»")
        receiver = task.assigned_to_id if task.created_by_id == request.user else task.created_by_id
        send_mail_notification(
            users=[receiver], 
            header="Изменение статуса в задаче", 
            text=f"Изменился статус задачи «{task.title}» проекта «{task.project_id.title}»."
        )
        return data
    
class ChangeTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tasks
        fields = ['title', 'description', 'due_date', 'priority', 'is_gittable', 'git_url', 'assigned_to_id']

    def validate(self, data):
        request = self.context['request']
        task = self.instance

        if task.created_by_id.id != request.user.id:

            log_user_action(user=request.user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на изменение задачи «{task.title}»",
                status='Ошибка прав доступа')
            
            raise serializers.ValidationError({'no_rights': 'У вас нет прав на изменение этой задачи.'})

        due_date = data.get('due_date')
        if due_date and due_date < now().date():
            raise serializers.ValidationError({'due_date': 'Некорректная дата сдачи задания. Дата не должна быть в прошлом.'})
        
        log_user_action(user=request.user, 
            action_name="Задачи", 
            description=f"Пользователь изменил задачу «{task.title}»")
        
        send_mail_notification(
            users=[task.assigned_to_id], 
            header="Изменения задачи", 
            text=f"Задача «{task.title}» проекта «{task.project_id.title}» была изменена."
        )

        return data
    
# Сериализатор для комментариев    
class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comments
        fields = ['id', 'task_id', 'text', 'user_id']
        read_only_fields = ['id', 'user_id']

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        task_id = attrs.get('task_id')
        task = Tasks.objects.get(id=getattr(task_id, 'id', task_id))

        is_project_leader = Users_projects.objects.filter(
            project_id=task.project_id,
            user_id=user,
            user_group_id__name="Руководитель проекта"
        ).exists()

        if not (task.created_by_id == user or task.assigned_to_id == user or is_project_leader):
            log_user_action(user=user, 
                action_name="Комментарии", 
                description=f"Пользователь послал запрос на создание комментария к задаче «{task.title}»",
                status='Ошибка прав доступа')
            raise serializers.ValidationError({'no_rights': 'Вам запрещено оставлять здесь комментарии.'})

        if not attrs.get('text'):
            raise serializers.ValidationError({'no_text': 'Текст комментария обязателен.'})

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        task = validated_data['task_id']
        comment = super().create({**validated_data, 'user_id': user})

        log_user_action(
            user=user,
            action_name="Комментарии",
            description=f"Пользователь успешно создал комментарий к задаче «{task.title}»",
            status='Успешно'
        )
        receiver = task.assigned_to_id if task.created_by_id == user else task.created_by_id
        send_mail_notification(
            users=[receiver], 
            header="Получен новый комментарий", 
            text=f"К задаче «{task.title}» проекта «{task.project_id.title}» добавлен новый комментарий."
        )

        return comment
    
class GetCommentSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='user_id.username', read_only=True)
    created_by_first_name = serializers.CharField(source='user_id.first_name', read_only=True)
    created_by_last_name = serializers.CharField(source='user_id.last_name', read_only=True)

    class Meta:
        model = Comments
        fields = [
            'id', 'task_id', 'text', 'created_at', 'is_edited',
            'created_by_username', 'created_by_first_name', 'created_by_last_name', 'user_id',
        ]

class UpdateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comments
        fields = ['text']
    
    def update(self, instance, validated_data):
        user = self.context['request'].user
        task_title = instance.task_id.title

        if instance.user_id != user:
            log_user_action(user=user, 
                action_name="Комментарии", 
                description=f"Пользователь послал запрос на изменение коммментария к задаче «{task_title}»",
                status='Ошибка прав доступа')
            raise serializers.ValidationError({'no_rights': 'Вы не можете редактировать этот комментарий.'})

        text = validated_data.get('text')
        if not text:
            raise serializers.ValidationError({'no_text': 'Текст комментария обязателен.'})

        instance.text = text
        instance.is_edited = True
        instance.save()
        log_user_action(user=user, 
            action_name="Комментарии", 
            description=f"Пользователь изменил комментарий к задаче «{task_title}»")
        return instance

class UserProfileSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=Users.objects.all(), message="Этот логин уже занят.")]
    )
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=Users.objects.all(), message="Пользователь с таким email уже существует.")]
    )

    class Meta:
        model = Users
        fields = ['username', 'first_name', 'last_name', 'current_password', 'new_password', 'email',
                  'notifications_status', 'theme_preference',]

    def validate(self, data):
        user = self.context['request'].user
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if new_password:
            if not current_password:
                raise serializers.ValidationError({'no_current_password':'Укажите текущий пароль для смены на новый.'})
            if not user.check_password(current_password):
                raise serializers.ValidationError({'wrong_password':'Неверный текущий пароль.'})

        return data

    def update(self, instance, validated_data):
        password = validated_data.pop('new_password', None)
        user = self.context['request'].user

        if password:
            instance.set_password(password)
        
        userInfo = super().update(instance, validated_data)
        log_user_action(user=user, 
            action_name="Аккаунты", 
            description=f"Пользователь изменил свои данные аккаунта")
        return userInfo
    
class UsersProjectsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users_projects
        fields = ['user_id', 'project_id', 'user_group_id']

    def update(self, instance, validated_data):
        user = self.context['request'].user
        executor_group = Groups.objects.get(name="Исполнитель")
        manager_group = Groups.objects.get(name="Менеджер")

        current_group = instance.user_group_id

        if current_group == executor_group:
            instance.user_group_id = manager_group  # Повышаем Исполнителя до Менеджера
        elif current_group == manager_group:
            instance.user_group_id = executor_group  # Понижаем Менеджера до Исполнителя
        else:
            raise serializers.ValidationError({'process_error':'Невозможно выполнить операцию, неверно указаны новые группы.'})
        
        instance.save()

        log_user_action(user=user, 
            action_name="Управление пользователями", 
            description=f"Руководитель изменил группу для {instance.user_id.username}")
        
        send_mail_notification(
            users=[instance.user_id],
            header="Изменения группы",
            text=f"Ваша группа в проекте «{instance.project_id.title}» была изменена."
        )
        
        return instance
        
class AllUserInfoSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'date_joined', 'last_login',
            'is_project_leader', 'is_admin', 'projects', 'is_active',
        ]

    def get_projects(self, user):
        user_projects = Users_projects.objects.filter(user_id=user.id).select_related('project_id', 'user_group_id')
        return [
            {
                'id': user_project.project_id.id,
                'project_name': user_project.project_id.title,
                'group_name': user_project.user_group_id.name,
            }
            for user_project in user_projects
        ]
    
class ChangeProjectLeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['is_project_leader']

    def update(self, instance, validated_data):
        user = self.context['request'].user
        instance.is_project_leader = not instance.is_project_leader
        instance.save()

        log_user_action(user=user, 
            action_name="Управление пользователями", 
            description=f"Администратор изменил право руководителя для {instance.username}")
        send_mail_notification(
            users=[instance], 
            header="Изменение Ваших прав в системе", 
            text=f"Ваши права управления проектами были изменены."
        )

        return instance
    
class ChangeActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['is_active']

    def update(self, instance, validated_data):
        user = self.context['request'].user
        instance.is_active = not instance.is_active
        instance.save()

        log_user_action(user=user, 
            action_name="Управление пользователями", 
            description=f"Администратор заблокировал пользователя {instance.username}")
        send_mail_notification(
            users=[instance], 
            header="Блокировка аккаунта", 
            text=f"Доступ к Вашему аккаунту был изменен."
        )

        return instance
    
class TaskStatusDistributionSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()

class TaskPriorityDistributionSerializer(serializers.Serializer):
    priority = serializers.CharField()
    count = serializers.IntegerField()

class LoadedUsersSerializer(serializers.Serializer):
    username = serializers.CharField()
    task_count = serializers.IntegerField()

class ActionTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action_types
        fields = ['id', 'name']

class GetUsersActionsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user_id.username', read_only=True)
    action_type_name = serializers.CharField(source='type_id.name', read_only=True)

    class Meta:
        model = User_actions
        fields = ['id', 'date_of_issue', 'username', 'action_type_name', 'description', 'status']


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not Users.objects.filter(email=value).exists():
            raise serializers.ValidationError({'no_user':'Пользователь с таким email не найден.'})
        return value

    def save(self):
        email = self.validated_data['email']
        user = Users.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{settings.FRONTEND_URL}/password-reset-confirm/{uid}/{token}/"

        send_mail(
            "Восстановление пароля",
            f"Перейдите по ссылке для сброса пароля: {reset_link}",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
    
# Сериализатор для формы восстановления пароля
class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)

    def save(self):
        uidb64 = self.context.get('uidb64')
        token = self.context.get('token')

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            raise serializers.ValidationError({'bad_url':'Неверная ссылка для сброса пароля'})

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({'wrong_token':'Неверный токен'})

        user.set_password(self.validated_data['new_password'])
        user.save()
        return user