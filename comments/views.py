# comments/views.py

from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView, DestroyAPIView
from management.base_access_views import BaseProjectAccessView
from rest_framework.exceptions import ValidationError
from .serializers import *
from .models import *


# Вью для создания комментария
class CreateCommentView(BaseProjectAccessView, CreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CreateCommentSerializer


# Вью для получения комментариев к задаче
class GetCommentsByTaskIdView(BaseProjectAccessView, ListAPIView):
    serializer_class = GetCommentSerializer

    def get_queryset(self):
        task = self.kwargs['pk']

        return Comment.objects.filter(task=task)


# Вью для редактирования комментария
class ChangeCommentView(UpdateAPIView):
    queryset = Comment.objects.all()
    serializer_class = UpdateCommentSerializer


# Вью для удаления комментария
class DeleteCommentView(DestroyAPIView):
    queryset = Comment.objects.all()

    def perform_destroy(self, instance):
        user = self.request.user
        task_title = instance.task.title

        if instance.created_by != user:
            log_user_action(
                user=user, 
                action_name="Комментарии", 
                description=f"Пользователь послал запрос на удаление комментария к задаче «{task_title}»",
                status='Ошибка прав доступа'
            )
            raise ValidationError({'no_rights': 'У Вас отсутствуют права для удаления этого комментария.'})

        instance.delete()

        log_user_action(
            user=user, 
            action_name="Комментарии", 
            description=f"Пользователь удалил комментарий к задаче «{task_title}»"
        )
