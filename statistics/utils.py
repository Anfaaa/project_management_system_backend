# statistics/utils.py

from rest_framework.exceptions import ValidationError
from management.permissions import IsAssigner
from management.models import User_project


def get_project_users(self, request, project):
    """
    Возвращает список ID пользователей проекта 
    в зависимости от группы пользователя, отправившего запрос.
    """
    is_manager =  IsAssigner().has_permission(request, self)

    if is_manager:
        return User_project.objects.filter(project=project, user_group__name='Исполнитель').values_list('user', flat=True)
    
    else:
        return User_project.objects.filter(project=project).exclude(user_group__name='Руководитель проекта').values_list('user', flat=True)


def check_project_id(kwargs):
    """
    Проверяет наличие ID проекта, переданного через параметры.
    """
    project_id = kwargs.get('project_id')

    if not project_id:
        raise ValidationError({'no_project_id': 'Не передан id проекта.'})
    return project_id