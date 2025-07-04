from django.urls import path
from . import views

app_name = 'transcriptions'

urlpatterns = [
    path('video/<int:video_id>/generate/', views.generate_transcript, name='generate_transcript'),
    path('video/<int:video_id>/get/', views.get_transcript, name='get_transcript'),
] 