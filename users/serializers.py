# users/serializers.py

from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from management.models import User_project
from rest_framework import serializers
from django.utils.timezone import now
from django.conf import settings
from .models import *
from .utils import *


# Сериализатор для регистрации пользователя
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="Этот логин уже занят.")]
    )
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=User.objects.all(), message="Пользователь с таким email уже существует.")]
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password')
    
    def create(self, validated_data):
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        log_user_action(
            user=user,
            action_name="Аккаунты",
            description=f"Пользователь создал аккаунт"
        )

        return user


# Сериализатор для входа пользователя в систему
class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError({'username': 'Неверный логин или пароль.'})
        
        if not user.check_password(password):
            raise serializers.ValidationError({'password': 'Неверный логин или пароль.'})

        if not user.is_active:
            log_user_action(
                user=user, 
                action_name="Аккаунты", 
                description=f"Пользователь совершил попытку входа в систему",
                status='Отказано в доступе'
            )
            raise serializers.ValidationError({'blocked': 'Аккаунт временно заблокирован.'})
        
        data['user'] = user

        return data
    
    def create(self, validated_data):
        user = validated_data['user']

        user.last_login = now()
        user.save(update_fields=['last_login'])

        refresh_token = RefreshToken.for_user(user)

        log_user_action(
            user=user, 
            action_name="Аккаунты", 
            description=f"Пользователь вошел в систему"
        )

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
        }


# Сериализатор для профиля пользователя (изменения данных о пользователе)
class UserProfileSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="Этот логин уже занят.")]
    )
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=User.objects.all(), message="Пользователь с таким email уже существует.")]
    )

    class Meta:
        model = User
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
        validated_data.pop('current_password', None)
        user = self.context['request'].user
        fields_changed = False

        for field in validated_data:
            if getattr(instance, field) != validated_data[field]:
                fields_changed = True
                break

        if password:
            instance.set_password(password)
        
        if fields_changed:
            instance = super().update(instance, validated_data)

            log_user_action(
                user=user, 
                action_name="Аккаунты", 
                description=f"Пользователь изменил свои данные аккаунта"
            )

        elif password:
            instance.save()
        
        return instance


# Сериализатор для получения всей информации о пользователях
class AllUserInfoSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'date_joined', 'last_login',
            'is_project_leader', 'is_admin', 'projects', 'is_active',
        ]

    def get_projects(self, user):
        user_projects = User_project.objects.filter(user=user.id).select_related('project', 'user_group')

        return [
            {
                'id': user_project.project.id,
                'project_name': user_project.project.title,
                'group_name': user_project.user_group.name,
            }
            for user_project in user_projects
        ]


# Сериализатор проверки пользователя и формирования письма для восстановления пароля
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError({'no_user':'Пользователь с таким email не найден.'})
        return value

    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{settings.FRONTEND_URL}/password-reset-confirm/{uid}/{token}/"

        send_mail_notification(
            users=[user], 
            header="Восстановление пароля", 
            text=f"Перейдите по ссылке для сброса пароля: {reset_link}"
        )


# Сериализатор для подтверждения восстановления и смены пароля
class ConfirmPasswordResetSerializer(serializers.Serializer):
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


# Сериализатор для получения типов действий пользователей в системе
class ActionTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action_type
        fields = ['id', 'name']


# Сериализатор для получения действий пользователей в системе
class GetUsersActionsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    action_type_name = serializers.CharField(source='type.name', read_only=True)

    class Meta:
        model = User_action
        fields = ['id', 'date_of_issue', 'username', 'action_type_name', 'description', 'status']
