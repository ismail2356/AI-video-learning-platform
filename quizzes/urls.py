from django.urls import path
from . import views

app_name = 'quizzes'

urlpatterns = [
    path('', views.quizzes_list, name='quizzes_list'),
    path('video/<int:video_id>/generate_quiz_ajax/', views.generate_quiz_ajax, name='generate_quiz_ajax'),
    path('video/<int:video_id>/create/', views.create_quiz, name='create_quiz'),
    path('delete/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    path('take/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('submit/<int:quiz_id>/', views.submit_quiz, name='submit_quiz'),
    path('results/<int:attempt_id>/', views.quiz_results, name='quiz_results'),
] 