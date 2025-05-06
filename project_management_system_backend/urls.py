from django.urls import path, include

urlpatterns = [
    path('api/', include('project_manager.urls')),
]
