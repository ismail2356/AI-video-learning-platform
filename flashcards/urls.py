from django.urls import path
from . import views

app_name = 'flashcards'

urlpatterns = [
    path('', views.flashcards_list, name='flashcards_list'),
    path('video/<int:video_id>/generate_flashcards_ajax/', views.generate_flashcards_ajax, name='generate_flashcards_ajax'),
    path('video/<int:video_id>/create/', views.create_flashcards, name='create_flashcards'),
    path('video/<int:video_id>/clean/', views.clean_flashcards, name='clean_flashcards'),
    path('fix-all/', views.fix_all_flashcards, name='fix_all_flashcards'),
    path('edit/<int:flashcard_id>/', views.edit_flashcard, name='edit_flashcard'),
    path('delete/<int:flashcard_id>/', views.delete_flashcard, name='delete_flashcard'),
] 