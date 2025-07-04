from django.urls import path
from . import views

app_name = 'videos'

urlpatterns = [
    path('', views.video_list, name='video_list'),
    path('upload/', views.video_upload, name='video_upload'),
    path('<int:video_id>/', views.video_detail, name='video_detail'),
    path('<int:video_id>/add_chat_message/', views.add_chat_message, name='add_chat_message'),
    path('<int:video_id>/add_note/', views.add_note, name='add_note'),
    path('<int:video_id>/add_chat_message_ajax/', views.add_chat_message_ajax, name='add_chat_message_ajax'),
    path('<int:video_id>/add_note_ajax/', views.add_note_ajax, name='add_note_ajax'),
    path('<int:video_id>/generate_summary/', views.generate_summary, name='generate_summary'),
    path('<int:video_id>/generate_flashcards/', views.generate_flashcards, name='generate_flashcards'),
    path('<int:video_id>/generate_quiz/', views.generate_quiz, name='generate_quiz'),
    path('<int:video_id>/delete/', views.delete_video, name='delete_video'),
] 