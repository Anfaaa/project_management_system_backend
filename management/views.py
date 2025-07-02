# management/views.py

from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from .base_access_views import BaseAdminAccessView, BaseProjectAccessView, BaseProjectLeaderAccessView
from rest_framework.exceptions import ValidationError
from .models import User_project, Project_request
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from projects.models import Project
from rest_framework import status
from users.models import User
from tasks.models import Task
from .serializers import *
from users.utils import *


# Вью для создания заявки на вступление в проект
class CreateProjectRequestView(CreateAPIView):
    serializer_class = CreateProjectRequestSerializer


# Вью для получения списка учасников проекта
class GetUsersInProjectView(ListAPIView):
    serializer_class = GetUsersSerializer

    def get_queryset(self):
        project = self.kwargs['pk']
        
        users_in_project = User_project.objects.filter(project=project).values('user')
        users = User.objects.filter(id__in=users_in_project)
        
        return users
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project_id'] = self.kwargs['pk']

        return context


# Вью для получения пользователей, не состоящих в проекте
class GetUsersNotInProjectView(ListAPIView):
    serializer_class = GetUsersSerializer

    def get_queryset(self):
        project = self.kwargs['pk']

        users_in_project = User_project.objects.filter(project=project).values('user')
        users_not_in_project = User.objects.exclude(id__in=users_in_project).exclude(is_admin=True)
        
        return users_not_in_project


# Вью для получения заявок на вступление в проект
class GetProjectRequestsView(ListAPIView):
    serializer_class = GetProjectRequestsSerializer

    def get_queryset(self):
        project = self.kwargs['pk']
        return Project_request.objects.filter(project=project).exclude(status="Принята")


# Вью для добавления пользователей в проект
class AddProjectMemberView(CreateAPIView):
    serializer_class = AddProjectMemberSerializer


# Вью для изменения статуса заявки на вступление в проект
class SetProjectRequestStatusView(UpdateAPIView):
    queryset = Project_request.objects.all()
    serializer_class = SetProjectRequestStatusSerializer


# Вью для исключения участника из проекта
class RemoveProjectMemberView(DestroyAPIView):
    def get_object(self):
        user = self.kwargs["user_id"]
        project = self.kwargs["project_id"]

        user_project = User_project.objects.filter(user=user, project=project).first()
        self.project = Project.objects.get(id=project)
        self.user_to_remove = User.objects.get(id=user)

        if not user_project:
            raise ValidationError({"user_not_found": "Пользователь не найден в проекте"})

        if not (self.project.created_by == self.request.user or self.request.user.id != user):
            log_user_action(
                user=self.request.user, 
                action_name="Вступление в проекты", 
                description=f"Пользователь послал запрос на исключение участника из проекта «{project.title}»",
                status='Ошибка прав доступа'
            )
            raise ValidationError({"no_rights": "У Вас отсутствуют права для исключения пользователя."})

        return user_project
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Удаляем все задачи, созданные исключаемым пользователем
        Task.objects.filter(created_by=self.user_to_remove, project=self.project).delete()

        # Переназначаем задачи, порученные пользователю, на создателя задачи
        assigned_tasks = Task.objects.filter(assigned_to=self.user_to_remove, project=self.project)
        
        for task in assigned_tasks:
            task.assigned_to = task.created_by
            task.save()

        # Удаление связи user-project
        instance.delete()

        log_user_action(
            user=request.user, 
            action_name="Вступление в проекты", 
            description=f"Руководитель исключил {self.user_to_remove} из проекта «{self.project.title}»"
        )

        send_mail_notification(
            users=[self.user_to_remove], 
            header="Исключение из проекта", 
            text=f"Вас исключили из проекта «{self.project.title}»."
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


# Вью для получения названия группы пользователя в проекте
class GetUserProjectGroupView(BaseProjectAccessView, RetrieveAPIView):
    serializer_class = UserProjectGroupSerializer

    def get_object(self):
        project = self.kwargs['project_id']
        user = self.request.user
        return get_object_or_404(User_project, project=project, user=user)


# Вью для изменения группы пользователя в проекте
class ChangeMemberGroupView(UpdateAPIView, BaseProjectLeaderAccessView):
    serializer_class = UsersProjectsSerializer

    def get_object(self):
        user = self.request.data.get('user_id')
        project = self.kwargs['project_id']
        try:
            return User_project.objects.get(user=user, project=project)
        except User_project.DoesNotExist:
            raise ValidationError({'member_not_found' : 'Запрашиваемый пользователь не найден в проекте.'})
        

# Вью для изменения права руководителя проектов (права управления проектами)
class ChangeProjectLeaderRightsView(BaseAdminAccessView, UpdateAPIView):
    serializer_class = ChangeProjectLeaderSerializer

    def get_object(self):
        return User.objects.get(id=self.request.data['user_id'])


# Вью для блокировки/активации пользовательских аккаунтов
class ChangeActivationView(BaseAdminAccessView, UpdateAPIView):
    serializer_class = ChangeActivationSerializer

    def get_object(self):
        return User.objects.get(id=self.request.data['user_id'])
