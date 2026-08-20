from django.urls import path
from .views import chat, upload_files

urlpatterns = [
    path("chat/", chat),
    path("upload/", upload_files),
]