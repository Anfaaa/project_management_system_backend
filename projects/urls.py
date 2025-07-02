# projects/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('create-project/', CreateProjectView.as_view(), name='create-project'),
    path('get-all-projects-list/', GetAllProjectsListView.as_view(), name='get-all-projects-list'),
    path('get-my-projects-list/', GetMyProjectsListView.as_view(), name='get-my-projects-list'),
    path('project/<int:pk>/get-details/', GetProjectDetailsView.as_view(), name='get-project-details'),
    path('project/<int:pk>/change-status/', ChangeProjectStatusView.as_view(), name='change-project-status'),
    path('project/<int:pk>/delete/', DeleteProjectView.as_view(), name='delete-project'),
    path('project/<int:pk>/change-info/', ChangeProjectView.as_view(), name='change-project-info'),
]