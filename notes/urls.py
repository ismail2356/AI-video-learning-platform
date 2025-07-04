from django.urls import path
from . import views

app_name = 'notes'

urlpatterns = [
    path('', views.notes_list, name='notes_list'),
    path('video/<int:video_id>/add_note_ajax/', views.add_note_ajax, name='add_note_ajax'),
] 