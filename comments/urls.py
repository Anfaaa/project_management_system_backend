# comments/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('task/<int:pk>/get-comments/', GetCommentsByTaskIdView.as_view(), name='task-get-comments'),
    path('task/<int:pk>/create-comment/', CreateCommentView.as_view(), name='create-comment'),
    path('comment/<int:pk>/delete/', DeleteCommentView.as_view(), name='delete-comment'),
    path('comment/<int:pk>/edit/', ChangeCommentView.as_view(), name='edit-comment'),
]