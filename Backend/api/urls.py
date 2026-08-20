from django.urls import path
from .views import chat, health, help_chat, upload_files

urlpatterns = [
    path("health/", health),
    path("help/", help_chat),
    path("chat/", chat),
    path("upload/", upload_files),
]
