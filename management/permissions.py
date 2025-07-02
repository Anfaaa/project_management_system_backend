# management/permissions.py

from .models import User_project
from tasks.models import Task
from rest_framework.permissions import BasePermission


def get_project(view, request):
    """
    Функция для получения project_id из url, через task или из тела запроса.
    """
    # Проверяем, есть ли project_id в url 
    project_id = view.kwargs.get('project_id')
    if project_id:
        return project_id

    # Проверяем, есть ли task_id в URL и извлекаем из него project_id
    task_id = view.kwargs.get('pk')
    if task_id:
        try:
            task = Task.objects.get(id=task_id)
            return task.project
        except Task.DoesNotExist:
            return None

    # Проверяем, есть ли project_id в теле запроса
    if 'project_id' in request.data:
        return request.data['project_id']

    # Проверяем, есть ли task_id в теле запроса и извлекаем из него project_id
    if 'task_id' in request.data:
        task_id_from_data = request.data['task_id']
        try:
            task = Task.objects.get(id=task_id_from_data)
            return task.project
        except Task.DoesNotExist:
            return None

    return None


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_admin:
            return True
        return False


class IsAssigner(BasePermission):
    """
    Разрешает доступ только тем пользователям, которые являются Менеджерами в проекте.
    """

    def has_permission(self, request, view):
        project = get_project(view, request)

        if project is None:
            return False

        user_project = User_project.objects.filter(user=request.user, project=project).first()

        if not user_project:
            return False
        
        if user_project.user_group.name == "Менеджер":
            return True

        return False

class IsProjectLeader(BasePermission):
    """
    Разрешает доступ только тем пользователям, которые являются руководителями проекта.
    """

    def has_permission(self, request, view):
        project = get_project(view, request)

        if project is None:
            return False

        user_project = User_project.objects.filter(user=request.user, project=project).first()

        if not user_project:
            return False

        if user_project.user_group.name == "Руководитель проекта":
            return True
        return False


class IsProjectParticipant(BasePermission):
    """
    Разрешает доступ только участникам проекта и администраторам.
    """

    def has_permission(self, request, view):
        if request.user.is_admin:
            return True
        
        project = get_project(view, request)

        if project is None:
            return False

        return User_project.objects.filter(user=request.user, project=project).exists()


class CanAssign(BasePermission):
    """
    Разрешает доступ, если пользователь является менеджером или руководителем проекта.
    """

    def has_permission(self, request, view):
        assigner_permission = IsAssigner()
        if assigner_permission.has_permission(request, view):
            return True

        leader_permission = IsProjectLeader()
        if leader_permission.has_permission(request, view):
            return True

        return False
    
class CanAssignOrAdmin(BasePermission):
    """
    Разрешает доступ, если пользователь является менеджером или руководителем проекта.
    """

    def has_permission(self, request, view):
        can_assign = CanAssign()
        if can_assign.has_permission(request, view):
            return True

        is_admin = IsAdmin()
        if is_admin.has_permission(request, view):
            return True

        return False
