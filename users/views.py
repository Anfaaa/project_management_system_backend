# users/views.py

from rest_framework.generics import CreateAPIView, GenericAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from management.base_access_views import BaseAdminAccessView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .utils import log_user_action
from rest_framework import status
from .serializers import *
from .models import *


# Вью для регистрации пользователей
class UserRegistrationView(CreateAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer


# Вью для входа пользователей в систему
class UserLoginView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)


# Вью для выхода пользователей из системы
class UserLogoutView(APIView):
    def post(self, request):
        log_user_action(
            user=request.user,
            action_name="Аккаунты",
            description=f"Пользователь вышел из системы"
        )
        return Response({"detail": "Выход из системы зафиксирован"})

    
# Вью для получения информации для профиля пользователя
class GetUserProfileInfo(RetrieveAPIView):
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


# Вью для изменения информации о пользователе в профиле
class ChangeUserProfileInfoView(UpdateAPIView):
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user


# Вью для удаления аккаунта пользователя
class DeleteUserAccount(DestroyAPIView):
    
    def get_object(self):
        return self.request.user


# Вью для получения полной информации о всех пользователях
class GetAllUsersInfoView(BaseAdminAccessView, ListAPIView):
    serializer_class = AllUserInfoSerializer
    queryset = User.objects.all()


# Вью для проверки пользователя и формирования письма для восстановления пароля
class PasswordResetView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer


# Вью для подтверждения восстановления и смены пароля
class PasswordResetConfirmView(CreateAPIView):
    serializer_class = ConfirmPasswordResetSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            'uidb64': self.kwargs.get('uidb64'),
            'token': self.kwargs.get('token'),
        })
        return context


# Вью для получения типов действий пользователей в системе
class GetActionTypesView(BaseAdminAccessView, ListAPIView):
    serializer_class = ActionTypesSerializer
    queryset = Action_type.objects.all()


# Вью для получения действий пользователей в системе
class GetUsersActionsView(BaseAdminAccessView, ListAPIView):
    serializer_class = GetUsersActionsSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        type_id = self.kwargs.get('type_id')

        return User_action.objects.filter(user=user_id, type=type_id)
