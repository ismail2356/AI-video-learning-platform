from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('video/<int:video_id>/add_chat_message_ajax/', views.add_chat_message_ajax, name='add_chat_message_ajax'),
    # URL'ler daha sonra eklenecek
] 