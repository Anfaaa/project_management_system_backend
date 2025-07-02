# users/models.py

from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    notifications_status = models.BooleanField(default=False)
    theme_preference = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_project_leader = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'notifications_status', 
                       'theme_preference', 'git_account_enabled', 'is_admin', 'is_project_leader']
    USERNAME_FIELD = 'username'

    @property
    def is_authenticated(self):
        return self.is_active

    @property
    def is_anonymous(self):
        return not self.is_authenticated
    
    def get_email_field_name(self):
        return 'email'    

    def __str__(self):
        return self.username
    
    def set_password(self, unencrypted_password):
        self.password = make_password(unencrypted_password)

    def check_password(self, unencrypted_password):
        return check_password(unencrypted_password, self.password)


class Action_type(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class User_action(models.Model):
    type = models.ForeignKey(
        Action_type, 
        related_name='type_actions',
        on_delete=models.PROTECT
    )
    user = models.ForeignKey(
        User, 
        related_name='user_actions',
        on_delete=models.CASCADE
    )
    date_of_issue = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    status = models.CharField(max_length=20)

    def __str__(self):
        return f"Действие типа '{self.type.name}' со статусом '{self.status}' пользователя {self.user.username}."