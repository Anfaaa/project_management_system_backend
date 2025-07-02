# urls.py

from django.urls import path, include

urlpatterns = [
    path('api/', include('users.urls')),
    path('api/', include('projects.urls')),
    path('api/', include('tasks.urls')),
    path('api/', include('comments.urls')),
    path('api/', include('management.urls')),
    path('api/', include('statistics.urls')),
]
