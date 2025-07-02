# tasks/views.py

from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from management.base_access_views import BaseAdminAccessView, BaseProjectAccessView, BaseCheckCanAssignView 
from rest_framework.exceptions import ValidationError
from django.db.models import F
from .serializers import *
from users.utils import *
from .models import *


# Вью для получения информации о всех задачах проекта
class GetAllTasksView(BaseAdminAccessView, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']

        return  Task.objects.filter(project=project_id)


# Вью для получения информации о "моих" задачах проекта
class GetMyTasksView(BaseProjectAccessView, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        user_id = self.request.user.id

        return Task.objects.filter(project=project_id, assigned_to=user_id)


# Вью для получения информации о назначенных "мной" задачах другим участникам проекта
class GetMyTasksToOthersView(BaseCheckCanAssignView, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        user_id = self.request.user.id
        
        return Task.objects.filter(project=project_id, created_by=user_id).exclude(assigned_to=user_id)
    

# Вью для получения информации о не личных задачах проекта
class GetNotPrivateTasksView(BaseProjectAccessView, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']

        return Task.objects.filter(project=project_id).exclude(created_by=F('assigned_to_id'))
    

# Вью для создания задачи
class CreateTaskView(BaseProjectAccessView, CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = CreateTaskSerializer


# Вью для получения полной информации о задаче
class GetTaskDetailsView(BaseProjectAccessView, RetrieveAPIView):
    serializer_class = GetTaskSerializer
    queryset = Task.objects.all()


# Вью для изменения статуса задачи
class ChangeTaskStatusView(BaseProjectAccessView, UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = ChangeTaskStatusSerializer


# Вью для изменения информации о задаче
class ChangeTaskView(UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = ChangeTaskSerializer


# Вью для удаления задачи
class DeleteTaskView(DestroyAPIView):
    queryset = Task.objects.all()

    def perform_destroy(self, instance):
        user = self.request.user

        if instance.created_by != user:
            log_user_action(
                user=user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на удаление задачи «{instance.title}»",
                status='Ошибка прав доступа'
            )
            raise ValidationError({'no_rights': 'У Вас отсутствуют права для удаления этой задачи.'})
        
        task_title = instance.title
        project_title = instance.project.title
        reciever = instance.assigned_to

        instance.delete()

        log_user_action(
            user=user, 
            action_name="Задачи", 
            description=f"Пользователь удалил задачу «{task_title}»."
        )
        send_mail_notification(
            users=[reciever], 
            header="Удаление задачи", 
            text=f"Задача «{task_title}» проекта «{project_title}» была удалена."
        )
