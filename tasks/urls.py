# tasks/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('project/<project_id>/get-all-tasks/', GetAllTasksView.as_view(), name='project-get-all-tasks'),
    path('project/<project_id>/get-my-tasks/', GetMyTasksView.as_view(), name='project-my-tasks'),
    path('project/<project_id>/get-my-tasks-to-others/', GetMyTasksToOthersView.as_view(), name='project-get-my-tasks-to-others'),
    path('project/<project_id>/get-not-private-tasks/', GetNotPrivateTasksView.as_view(), name='project-get-not-private-tasks'),
    path('create-task/', CreateTaskView.as_view(), name='create-task'),
    path('task/<int:pk>/get-details/', GetTaskDetailsView.as_view(), name='get-task-details'),
    path('task/<int:pk>/change-status/', ChangeTaskStatusView.as_view(), name='change-task-status'),
    path('task/<int:pk>/delete/', DeleteTaskView.as_view(), name='delete-task'),
    path('task/<int:pk>/change-info/', ChangeTaskView.as_view(), name='change-task-info'),
]