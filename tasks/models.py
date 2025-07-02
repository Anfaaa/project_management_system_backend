# tasks/models.py

from django.db import models
from users.models import User
from projects.models import Project


class Task(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20)
    priority = models.CharField(max_length=20)
    is_gittable = models.BooleanField(default=False)
    git_url = models.CharField(max_length=150, blank=True)
    project = models.ForeignKey(
        Project,
        related_name='project_tasks',
        on_delete=models.CASCADE
    )
    assigned_to = models.ForeignKey(
        User,
        related_name='user_tasks_to_do',
        on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        User,
        related_name='user_created_tasks',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Задание '{self.title}' в проекте '{self.project.title}'."
