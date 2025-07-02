# management/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('project/<int:pk>/create-request/', CreateProjectRequestView.as_view(), name='create-project-request'),
    path('project/<int:pk>/get-none-users/', GetUsersNotInProjectView.as_view(), name='project-none-users'),
    path('project/<int:pk>/get-users/', GetUsersInProjectView.as_view(), name='project-users'),
    path('project/<int:pk>/get-requests/', GetProjectRequestsView.as_view(), name='project-get-requests'),
    path('project/<int:pk>/add-member/', AddProjectMemberView.as_view(), name='project-add-member'),
    path('project/<project_id>/request/<int:pk>/set-status/', SetProjectRequestStatusView.as_view(), name='project-set-request-status'),
    path('project/<project_id>/remove-member/<user_id>/', RemoveProjectMemberView.as_view(), name='project-remove-member'),
    path('project/<project_id>/get-user-group/', GetUserProjectGroupView.as_view(), name='get-user-project-group'),
    path('project/<project_id>/change-member-group/', ChangeMemberGroupView.as_view(), name='project-change-member-group'),
    path('change-project-leader-rights/', ChangeProjectLeaderRightsView.as_view(), name='change-project-leader-rights'),
    path('change-account-activation/', ChangeActivationView.as_view(), name='change-account-activation'),
]