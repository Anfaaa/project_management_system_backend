# projects/views.py

from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.exceptions import ValidationError
from management.models import User_project
from users.utils import log_user_action
from .serializers import *
from .models import *


# Вью для создания проекта
class CreateProjectView(CreateAPIView):
    queryset = Project.objects.all()
    serializer_class = CreateProjectSerializer


# Вью для получения информации о всех проектах
class GetAllProjectsListView(ListAPIView):
    queryset = Project.objects.all()
    serializer_class = GetProjectSerializer


# Вью для получения информации о "моих" проектах
class GetMyProjectsListView(ListAPIView):
    serializer_class = GetProjectSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        current_user_projects = User_project.objects.filter(user=user_id).values('project')

        return Project.objects.filter(id__in=current_user_projects)


# Вью для получения полной информации о проекте
class GetProjectDetailsView(RetrieveAPIView):
    serializer_class = GetProjectSerializer
    queryset = Project.objects.all()


# Вью для изменения статуса проекта
class ChangeProjectStatusView(UpdateAPIView):
    queryset = Project.objects.all()
    serializer_class = ChangeProjectStatusSerializer


# Вью для изменения информации о проекте
class ChangeProjectView(UpdateAPIView):
    queryset = Project.objects.all()
    serializer_class = ChangeProjectSerializer


# Вью для удаления проекта
class DeleteProjectView(DestroyAPIView):
    queryset = Project.objects.all()

    def perform_destroy(self, instance):
        user = self.request.user

        if instance.created_by != user:
            log_user_action(
                user=user, 
                action_name="Проекты", 
                description=f"Пользователь послал запрос на удаление проекта «{instance.title}»",
                status='Ошибка прав доступа'
            )
            raise ValidationError({'no_rights': 'У Вас отсутствуют права для удаления проекта.'})
        
        project_title = instance.title

        instance.delete()
        
        log_user_action(
            user=user,
            action_name="Проекты",
            description=f"Руководитель удалил проект «{project_title}»"
        )