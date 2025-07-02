from django.db import models
from users.models import User
from tasks.models import Task


class Comment(models.Model):
    created_by = models.ForeignKey(
        User,
        related_name='user_comments',
        on_delete=models.CASCADE
    )
    task = models.ForeignKey(
        Task,
        related_name='task_comments',
        on_delete=models.CASCADE
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Комментарий пользователя {self.user_id.username} на задание '{self.task.title}'."
