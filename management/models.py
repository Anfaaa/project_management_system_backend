# management/models.py

from django.db import models
from users.models import User
from projects.models import Project


class Group(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name
    

class User_project(models.Model):
    project = models.ForeignKey(
        Project,
        related_name='project_user',
        on_delete=models.CASCADE
    )
    user_group = models.ForeignKey(
        Group,
        related_name = 'group_users',
        on_delete=models.PROTECT
    )
    user = models.ForeignKey(
        User,
        related_name='user_project',
        on_delete=models.CASCADE
    )
    date_joined_project = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Пользователь {self.user.username} в проекте '{self.project.title}' с ролью - '{self.user_group.name}'."


class Project_request(models.Model):
    project = models.ForeignKey(
        Project,
        related_name='project_requests',
        on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        User,
        related_name='user_requests',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)

    def __str__(self):
        return f"Запрос пользователя {self.created_by.username} в проект '{self.project.title}' со статусом '{self.status}'."
