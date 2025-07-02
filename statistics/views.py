# statistics/views.py

from management.base_access_views import BaseCheckNotOrdinaryUserView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from django.db.models import F, Count, Q
from users.models import User
from tasks.models import Task
from .serializers import *
from .utils import *


# Вью для получения данных о распределении задач проекта по статусам
class TaskStatusDistributionView(BaseCheckNotOrdinaryUserView, GenericAPIView):
    serializer_class = TaskStatusDistributionSerializer

    def get(self, request, *args, **kwargs):
        project = check_project_id(kwargs)

        tasks = Task.objects.filter(project=project).exclude(created_by=F('assigned_to'))
        status_distribution = tasks.values('status').annotate(count=Count('id'))

        return Response(status_distribution)


# Вью для получения данных о распределении задач проекта по приоритетам
class TaskPriorityDistributionView(BaseCheckNotOrdinaryUserView, GenericAPIView):
    serializer_class = TaskPriorityDistributionSerializer

    def get(self, request, *args, **kwargs):
        project = check_project_id(kwargs)

        tasks = Task.objects.filter(project=project).exclude(created_by=F('assigned_to'))
        priority_distribution = tasks.values('priority').annotate(count=Count('id'))

        return Response(priority_distribution)


# Вью для получения данных о самых загруженных участниках проекта
class OverloadedUsersView(BaseCheckNotOrdinaryUserView, GenericAPIView):
    serializer_class = LoadedUsersSerializer

    def get(self, request, *args, **kwargs):
        project = check_project_id(kwargs)
        project_users = get_project_users(self, request, project)

        overloaded_users = User.objects.filter(id__in=project_users).annotate(
            task_count=Count(
                'user_tasks_to_do',
                filter=~Q(user_tasks_to_do__status__in=['Отменено', 'Приостановлено'])&
                    ~Q(user_tasks_to_do__created_by=F('user_tasks_to_do__assigned_to'))
            )
        ).order_by('-task_count')[:5]

        return Response(overloaded_users.values('username', 'task_count'))


# Вью для получения данных о самых незагруженных участниках проекта
class UnderloadedUsersView(BaseCheckNotOrdinaryUserView, GenericAPIView):
    serializer_class = LoadedUsersSerializer

    def get(self, request, *args, **kwargs):
        project = check_project_id(kwargs)
        project_users = get_project_users(self, request, project)

        underloaded_users = User.objects.filter(id__in=project_users).annotate(
            task_count=Count(
                'user_tasks_to_do',
                filter=~Q(user_tasks_to_do__status__in=['Отменено', 'Приостановлено'])&
                    ~Q(user_tasks_to_do__created_by=F('user_tasks_to_do__assigned_to'))
            )
        ).order_by('task_count')[:5]

        return Response(underloaded_users.values('username', 'task_count'))


# Вью для получения данных о распределении задач пользователя в проекте по статусам
class TaskDistributionByUserView(BaseCheckNotOrdinaryUserView, GenericAPIView):
    serializer_class = TaskStatusDistributionSerializer

    def get(self, request, *args, **kwargs):
        user = kwargs.get('user_id')
        project = check_project_id(kwargs)

        tasks = Task.objects.filter(assigned_to=user, project=project).exclude(created_by=F('assigned_to'))
        task_distribution = tasks.values('status').annotate(count=Count('id'))

        return Response(task_distribution)