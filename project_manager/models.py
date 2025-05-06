from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Users(models.Model):
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    notifications_status = models.BooleanField(default=False)
    theme_preference = models.BooleanField(default=False)
    git_account_enabled = models.BooleanField(default=False)
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


class Action_types(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class User_actions(models.Model):
    type_id = models.ForeignKey(
        Action_types, 
        related_name='type_actions',
        on_delete=models.PROTECT
    )
    user_id = models.ForeignKey(
        Users, 
        related_name='user_actions',
        on_delete=models.CASCADE
    )
    date_of_issue = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    status = models.CharField(max_length=20)

    def __str__(self):
        return f"Действие типа '{self.type_id.name}' со статусом '{self.status}' пользователя {self.user_id.username}."
    

class Notifications(models.Model):
    message = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    user_id = models.ForeignKey(
        Users,
        related_name='user_notifications_status',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Сообщение от {self.date} пользователю {self.user_id.username}."
    

class Projects(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20)
    priority = models.CharField(max_length=20)
    is_gittable = models.BooleanField(default=False)
    git_url = models.CharField(max_length=150, blank=True)
    created_by_id = models.ForeignKey(
        Users,
        related_name='user_created_projects',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.title


class Groups(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name
    

class Users_projects(models.Model):
    project_id = models.ForeignKey(
        Projects,
        related_name='project_user',
        on_delete=models.CASCADE
    )
    user_group_id = models.ForeignKey(
        Groups,
        related_name = 'group_users',
        on_delete=models.PROTECT
    )
    user_id = models.ForeignKey(
        Users,
        related_name='user_project',
        on_delete=models.CASCADE
    )
    date_joined_project = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Пользователь {self.user_id.username} в проекте '{self.project_id.title}' с ролью - '{self.user_group_id.name}'."


class Project_requests(models.Model):
    project_id = models.ForeignKey(
        Projects,
        related_name='project_requests',
        on_delete=models.CASCADE
    )
    created_by_id = models.ForeignKey(
        Users,
        related_name='user_requests',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)

    def __str__(self):
        return f"Запрос пользователя {self.created_by_id.username} в проект '{self.project_id.title}' со статусом '{self.status}'."

    
class Tasks(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20)
    priority = models.CharField(max_length=20)
    is_gittable = models.BooleanField(default=False)
    git_url = models.CharField(max_length=150, blank=True)
    project_id = models.ForeignKey(
        Projects,
        related_name='project_tasks',
        on_delete=models.CASCADE
    )
    assigned_to_id = models.ForeignKey(
        Users,
        related_name='user_tasks_to_do',
        on_delete=models.CASCADE
    )
    created_by_id = models.ForeignKey(
        Users,
        related_name='user_created_tasks',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Задание '{self.title}' в проекте '{self.project_id.title}'."


class Comments(models.Model):
    user_id = models.ForeignKey(
        Users,
        related_name='user_comments',
        on_delete=models.CASCADE
    )
    task_id = models.ForeignKey(
        Tasks,
        related_name='task_comments',
        on_delete=models.CASCADE
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Комментарий пользователя {self.user_id.username} на задание '{self.task_id.title}'."
    