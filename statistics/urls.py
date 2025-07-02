# statistics/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('project/<project_id>/statistics/status-distribution/', TaskStatusDistributionView.as_view(), name='project-statistics-status-distribution'),
    path('project/<project_id>/statistics/priority-distribution/', TaskPriorityDistributionView.as_view(), name='project-statistics-priority-distribution'),
    path('project/<project_id>/statistics/overloaded-users/', OverloadedUsersView.as_view(), name='project-statistics-overloaded-users'),
    path('project/<project_id>/statistics/underloaded-users/', UnderloadedUsersView.as_view(), name='project-statistics-underloaded-users'),
    path('project/<project_id>/statistics/task-status-distribution/user/<user_id>/', TaskDistributionByUserView.as_view(), name='project-statistics-user-task-distribution'),
]