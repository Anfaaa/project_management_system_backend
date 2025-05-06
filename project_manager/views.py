# views.py

from django.shortcuts import get_object_or_404
from rest_framework.generics import CreateAPIView, GenericAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework import status
from django.db.models import F, Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Users, Projects, Users_projects
from .serializers import *
from .permissions import *

class ProjectAccessMixin(GenericAPIView):
    permission_classes = [IsProjectParticipant]

class AdminAccessMixin(GenericAPIView):
    permission_classes = [IsAdmin]

class ProjectLeaderAccessMixin(GenericAPIView):
    permission_classes = [IsProjectLeader]

class AssignerAccessMixin(GenericAPIView):
    permission_classes = [IsAssigner]

class CheckCanAssignMixin(GenericAPIView):
    permission_classes = [CanAssign]

class CheckNotBaseUserMixin(GenericAPIView):
    permission_classes = [CanAssignOrAdmin]

def check_project_id(kwargs):
    project_id = kwargs.get('project_id')

    if not project_id:
        raise ValidationError({'no_project_id': 'Не передан id проекта.'})
    return project_id

class UserRegistrationView(CreateAPIView):
    permission_classes = [AllowAny]
    queryset = Users.objects.all()
    serializer_class = UserRegistrationSerializer

class UserLoginView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class UserLogoutView(APIView):
    def post(self, request):
        log_user_action(
            user=request.user,
            action_name="Аккаунты",
            description=f"Пользователь вышел из системы"
        )
        return Response({"detail": "Выход из системы зафиксирован"})
    
class CreateProjectView(CreateAPIView):
    queryset = Projects.objects.all()
    serializer_class = CreateProjectSerializer

class GetAllProjectsListView(ListAPIView):
    queryset = Projects.objects.all()
    serializer_class = GetProjectSerializer

class GetMyProjectsListView(ListAPIView):
    serializer_class = GetProjectSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        current_user_projects = Users_projects.objects.filter(user_id=user_id).values('project_id')
        return Projects.objects.filter(id__in=current_user_projects)

class GetProjectDetailsView(RetrieveAPIView):
    serializer_class = GetProjectSerializer
    queryset = Projects.objects.all()

class ChangeProjectStatusView(UpdateAPIView):
    queryset = Projects.objects.all()
    serializer_class = ChangeProjectStatusSerializer

class DeleteProjectView(DestroyAPIView):
    queryset = Projects.objects.all()

    def perform_destroy(self, instance):
        request = self.request
        if instance.created_by_id != request.user:
            log_user_action(user=request.user, 
                action_name="Проекты", 
                description=f"Пользователь послал запрос на удаление проекта «{instance.title}»",
                status='Ошибка прав доступа')
            raise ValidationError({'no_rights': 'У Вас отсутствуют права для удаления проекта.'})
        log_user_action(user=request.user, 
            action_name="Проекты", 
            description=f"Руководитель удалил проект «{instance.title}»")
        instance.delete()

class ChangeProjectView(UpdateAPIView):
    queryset = Projects.objects.all()
    serializer_class = ChangeProjectSerializer

class CreateProjectRequestView(CreateAPIView):
    serializer_class = CreateProjectRequestSerializer


class GetUsersInProjectView(ListAPIView):
    serializer_class = GetUsersSerializer

    def get_queryset(self):
        project_id = self.kwargs['pk']
        
        users_in_project = Users_projects.objects.filter(project_id=project_id).values('user_id')
        users = Users.objects.filter(id__in=users_in_project)
        
        return users
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project_id'] = self.kwargs['pk']
        return context
    
class GetUsersNotInProjectView(ListAPIView):
    serializer_class = GetUsersSerializer

    def get_queryset(self):
        project_id = self.kwargs['pk']

        user_ids_in_project = Users_projects.objects.filter(project_id=project_id).values('user_id')
        users_not_in_project = Users.objects.exclude(id__in=user_ids_in_project).exclude(is_admin=True)
        
        return users_not_in_project
    
class GetProjectRequestsView(ListAPIView):
    serializer_class = GetProjectRequestsSerializer

    def get_queryset(self):
        project_id = self.kwargs['pk']
        return Project_requests.objects.filter(project_id=project_id).exclude(status="Принята")
    
class AddProjectMemberView(CreateAPIView):
    serializer_class = AddProjectMemberSerializer

class SetProjectRequestStatusView(UpdateAPIView):
    queryset = Project_requests.objects.all()
    serializer_class = SetProjectRequestStatusSerializer

class RemoveProjectMemberView(DestroyAPIView):
    def get_object(self):
        user_id = self.kwargs["user_id"]
        project_id = self.kwargs["project_id"]

        user_project = Users_projects.objects.filter(user_id=user_id, project_id=project_id).first()
        project = Projects.objects.get(id=project_id)
        user_to_remove = Users.objects.get(id=user_id)

        if not user_project:
            raise ValidationError({"user_not_found": "Пользователь не найден в проекте"})

        if not (Projects.objects.filter(id=project_id, created_by_id=self.request.user.id).exists() or self.request.user.id != user_id):
            log_user_action(user=self.request.user, 
                action_name="Вступление в проекты", 
                description=f"Пользователь послал запрос на исключение участника из проекта «{project.title}»",
                status='Ошибка прав доступа')
            raise ValidationError({"no_rights": "У Вас отсутствуют права для исключения пользователя."})

        log_user_action(user=self.request.user, 
            action_name="Вступление в проекты", 
            description=f"Руководитель исключил {user_to_remove} из проекта «{project.title}»")
        
        send_mail_notification(
            users=[user_to_remove], 
            header="Исключение из проекта", 
            text=f"Вас исключили из проекта «{project.title}»."
        )

        return user_project
    
class GetAllTasksView(AdminAccessMixin, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        return  Tasks.objects.filter(project_id=project_id)
    
class GetMyTasksView(ProjectAccessMixin, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        user_id = self.request.user.id
        return Tasks.objects.filter(project_id=project_id, assigned_to_id=user_id)
    
class GetMyTasksToOthersView(CheckCanAssignMixin, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        user_id = self.request.user.id
        return Tasks.objects.filter(project_id=project_id, created_by_id=user_id).exclude(assigned_to_id=user_id)
    
class GetNotPrivateTasksView(ProjectAccessMixin, ListAPIView):
    serializer_class = GetTaskSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        return  Tasks.objects.filter(project_id=project_id).exclude(created_by_id=F('assigned_to_id'))
    
class GetUserProjectGroupView(ProjectAccessMixin, RetrieveAPIView):
    serializer_class = UserProjectGroupSerializer

    def get_object(self):
        project_id = self.kwargs['project_id']
        user = self.request.user
        return get_object_or_404(Users_projects, project_id=project_id, user_id=user)
    
class CreateTaskView(ProjectAccessMixin, CreateAPIView):
    queryset = Tasks.objects.all()
    serializer_class = CreateTaskSerializer

class GetTaskDetailsView(ProjectAccessMixin, RetrieveAPIView):
    serializer_class = GetTaskSerializer
    queryset = Tasks.objects.all()

class ChangeTaskStatusView(UpdateAPIView):
    queryset = Tasks.objects.all()
    serializer_class = ChangeTaskStatusSerializer

class DeleteTaskView(DestroyAPIView):
    queryset = Tasks.objects.all()

    def perform_destroy(self, instance):
        request = self.request
        if instance.created_by_id != request.user:
            log_user_action(user=request.user, 
                action_name="Задачи", 
                description=f"Пользователь послал запрос на удаление задачи «{instance.title}»",
                status='Ошибка прав доступа')
            raise ValidationError({'no_rights': 'У Вас отсутствуют права для удаления этой задачи.'})
        
        log_user_action(user=request.user, 
            action_name="Задачи", 
            description=f"Пользователь удалил задачу «{instance.title}»")
        send_mail_notification(
            users=[instance.assigned_to_id], 
            header="Удаление задачи", 
            text=f"Задача «{instance.title}» проекта «{instance.project_id.title}» была удалена."
        )
        instance.delete()

class ChangeTaskView(ProjectAccessMixin, UpdateAPIView):
    queryset = Tasks.objects.all()
    serializer_class = ChangeTaskSerializer

class CreateCommentView(CreateAPIView):
    queryset = Comments.objects.all()
    serializer_class = CreateCommentSerializer

class GetCommentsByTaskIdView(ProjectAccessMixin, ListAPIView):
    serializer_class = GetCommentSerializer

    def get_queryset(self):
        task_id = self.kwargs['pk']
        return  Comments.objects.filter(task_id=task_id)
    
class DeleteCommentView(DestroyAPIView):
    queryset = Comments.objects.all()

    def perform_destroy(self, instance):
        request = self.request
        if instance.user_id != request.user:
            log_user_action(user=request.user, 
                action_name="Комментарии", 
                description=f"Пользователь послал запрос на удаление комментария к задаче «{instance.task_id.title}»",
                status='Ошибка прав доступа')
            raise ValidationError({'no_rights': 'У Вас отсутствуют права для удаления этого комментария.'})
        
        log_user_action(user=request.user, 
            action_name="Комментарии", 
            description=f"Пользователь удалил комментарий к задаче «{instance.task_id.title}»")
        instance.delete()

class ChangeCommentView(UpdateAPIView):
    queryset = Comments.objects.all()
    serializer_class = UpdateCommentSerializer

class GetUserProfileInfo(RetrieveAPIView):
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

class ChangeUserProfileInfoView(UpdateAPIView):
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user

class DeleteUserAccount(DestroyAPIView):
    
    def get_object(self):
        return self.request.user
    
class ChangeMemberGroupView(UpdateAPIView, ProjectLeaderAccessMixin):
    serializer_class = UsersProjectsSerializer

    def get_object(self):
        user_id = self.request.data.get('user_id')
        project_id = self.kwargs['project_id']
        try:
            return Users_projects.objects.get(user_id=user_id, project_id=project_id)
        except Users_projects.DoesNotExist:
            raise ValidationError({'member_not_found' : 'Запрашиваемый пользователь не найден в проекте.'})
        
class GetAllUsersInfoView(AdminAccessMixin, ListAPIView):
    serializer_class = AllUserInfoSerializer
    queryset = Users.objects.all()

class ChangeProjectLeaderRightsView(AdminAccessMixin, UpdateAPIView):
    serializer_class = ChangeProjectLeaderSerializer

    def get_object(self):
        return Users.objects.get(id=self.request.data['user_id'])

class ChangeActivationView(AdminAccessMixin, UpdateAPIView):
    serializer_class = ChangeActivationSerializer

    def get_object(self):
        return Users.objects.get(id=self.request.data['user_id'])

class TaskStatusDistributionView(CheckNotBaseUserMixin, GenericAPIView):
    serializer_class = TaskStatusDistributionSerializer

    def get(self, request, *args, **kwargs):
        project_id = check_project_id(kwargs)
        tasks = Tasks.objects.filter(project_id=project_id).exclude(created_by_id=F('assigned_to_id'))

        # Распределение задач по статусам
        status_distribution = tasks.values('status').annotate(count=Count('id'))
        return Response(status_distribution)
    
class TaskPriorityDistributionView(CheckNotBaseUserMixin, GenericAPIView):
    serializer_class = TaskPriorityDistributionSerializer

    def get(self, request, *args, **kwargs):
        project_id = check_project_id(kwargs)
        tasks = Tasks.objects.filter(project_id=project_id).exclude(created_by_id=F('assigned_to_id'))

        # Распределение задач по приоритетам
        priority_distribution = tasks.values('priority').annotate(count=Count('id'))
        return Response(priority_distribution)
    
def get_project_user_ids(self, request, project_id):
    """
    Возвращает список ID пользователей, участвующих в проекте.
    """
    is_manager =  IsAssigner().has_permission(request, self)
    if is_manager:
        return Users_projects.objects.filter(project_id=project_id, user_group_id__name='Исполнитель').values_list('user_id', flat=True)
    else:
        return Users_projects.objects.filter(project_id=project_id).exclude(user_group_id__name='Руководитель проекта').values_list('user_id', flat=True)

    
class OverloadedUsersView(CheckNotBaseUserMixin, GenericAPIView):
    serializer_class = LoadedUsersSerializer

    def get(self, request, *args, **kwargs):
        project_id = check_project_id(kwargs)
        project_users = get_project_user_ids(self, request, project_id)

        overloaded_users = Users.objects.filter(id__in=project_users).annotate(
            task_count=Count(
                'user_tasks_to_do',
                filter=~Q(user_tasks_to_do__status__in=['Отменено', 'Приостановлено'])&
                    ~Q(user_tasks_to_do__created_by_id=F('user_tasks_to_do__assigned_to_id'))
            )
        ).order_by('-task_count')[:5]

        return Response(overloaded_users.values('username', 'task_count'))
    
class UnderloadedUsersView(CheckNotBaseUserMixin, GenericAPIView):
    serializer_class = LoadedUsersSerializer

    def get(self, request, *args, **kwargs):
        project_id = check_project_id(kwargs)
        project_users = get_project_user_ids(self, request, project_id)

        underloaded_users = Users.objects.filter(id__in=project_users).annotate(
            task_count=Count(
                'user_tasks_to_do',
                filter=~Q(user_tasks_to_do__status__in=['Отменено', 'Приостановлено'])&
                    ~Q(user_tasks_to_do__created_by_id=F('user_tasks_to_do__assigned_to_id'))
            )
        ).order_by('task_count')[:5]

        return Response(underloaded_users.values('username', 'task_count'))

class TaskDistributionByUserView(CheckNotBaseUserMixin, GenericAPIView):
    serializer_class = TaskStatusDistributionSerializer

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id')
        project_id = check_project_id(kwargs)

        tasks = Tasks.objects.filter(assigned_to_id=user_id, project_id=project_id).exclude(created_by_id=F('assigned_to_id'))

        # Распределение задач по статусам для пользователя
        task_distribution = tasks.values('status').annotate(count=Count('id'))
        return Response(task_distribution)
    
class GetActionTypesView(AdminAccessMixin, ListAPIView):
    serializer_class = ActionTypesSerializer
    queryset = Action_types.objects.all()

class GetUsersActionsView(AdminAccessMixin, ListAPIView):
    serializer_class = GetUsersActionsSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        type_id = self.kwargs.get('type_id')

        return User_actions.objects.filter(user_id=user_id, type_id=type_id)
    

class PasswordResetView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer

class PasswordResetConfirmView(CreateAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            'uidb64': self.kwargs.get('uidb64'),
            'token': self.kwargs.get('token'),
        })
        return context