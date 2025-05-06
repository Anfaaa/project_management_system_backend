# permissions.py

from project_manager.models import Tasks, Users_projects, Groups
from rest_framework.permissions import BasePermission

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
        project_id = get_project_id_from_task_or_url(view, request)

        if project_id is None:
            return False

        user_project = Users_projects.objects.filter(user_id=request.user, project_id=project_id).first()

        if not user_project:
            return False
        
        if user_project.user_group_id.name == "Менеджер":
            return True

        return False

class IsProjectLeader(BasePermission):
    """
    Разрешает доступ только тем пользователям, которые являются руководителями проекта.
    """

    def has_permission(self, request, view):
        project_id = get_project_id_from_task_or_url(view, request)

        if project_id is None:
            print('project_id is None')
            return False

        user_project = Users_projects.objects.filter(user_id=request.user, project_id=project_id).first()

        if not user_project:
            print('not user_project')
            return False

        if user_project.user_group_id.name == "Руководитель проекта":
            return True
        print('other problem')
        return False


class IsProjectParticipant(BasePermission):
    """
    Разрешает доступ только участникам проекта и администраторам.
    """

    def has_permission(self, request, view):
        if request.user.is_admin:
            return True
        
        project_id = get_project_id_from_task_or_url(view, request)

        if project_id is None:
            return False  # Если не удалось получить project_id, доступ запрещен.

        # Проверяем, является ли пользователь участником проекта
        return Users_projects.objects.filter(user_id=request.user, project_id=project_id).exists()


def get_project_id_from_task_or_url(view, request):
    """
    Функция для получения project_id - либо из task_id, либо из переданного параметра в URL.
    """

    # Проверяем, есть ли в URL project_id
    project_id = view.kwargs.get('project_id')  # Получаем project_id из URL, если оно есть
    if project_id:
        return project_id  # Если это проект, возвращаем его ID

    # Если project_id нет, проверяем есть ли task_id в URL
    task_id = view.kwargs.get('pk')  # В случае с задачей, это будет pk
    if task_id:
        try:
            task = Tasks.objects.get(id=task_id)  # Ищем задачу по ID
            return task.project_id  # Если задача найдена, возвращаем ее project_id
        except Tasks.DoesNotExist:
            return None  # Если задача не найдена, возвращаем None

    # Если project_id и task_id нет в URL, пытаемся найти их в теле запроса (например, в данных формы или тела JSON)
    # Например, если нужно передавать project_id или task_id через параметры POST, можно сделать так:
    if 'project_id' in request.data:
        return request.data['project_id']  # Извлекаем project_id из данных запроса

    if 'task_id' in request.data:
        task_id_from_data = request.data['task_id']
        try:
            task = Tasks.objects.get(id=task_id_from_data)
            return task.project_id  # Извлекаем project_id через task_id
        except Tasks.DoesNotExist:
            return None

    return None  # Если project_id или task_id нет, возвращаем None

class CanAssign(BasePermission):
    """
    Разрешает доступ, если пользователь является менеджером или руководителем проекта.
    """

    def has_permission(self, request, view):
        is_assigner_permission = IsAssigner()
        if is_assigner_permission.has_permission(request, view):
            return True

        is_project_leader_permission = IsProjectLeader()
        if is_project_leader_permission.has_permission(request, view):
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