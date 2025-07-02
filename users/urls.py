# users/urls.py

from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from .views import *


urlpatterns = [
    path('registration/', UserRegistrationView.as_view(), name='user-registration'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('get-user-profile-info/', GetUserProfileInfo.as_view(), name='get-user-profile-info'),
    path('change-user-profile-info/', ChangeUserProfileInfoView.as_view(), name='change-user-profile-info'),
    path('delete-user-account/', DeleteUserAccount.as_view(), name='delete-user-account'),
    path('get-all-users-info/', GetAllUsersInfoView.as_view(), name='get-all-users-info'),
    path('get-action-types/', GetActionTypesView.as_view(), name='get-action-types'),
    path('get-actions/user/<user_id>/type/<type_id>/', GetUsersActionsView.as_view(), name='get-user-actions'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]