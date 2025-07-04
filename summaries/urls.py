from django.urls import path
from . import views

app_name = 'summaries'

urlpatterns = [
    path('video/<int:video_id>/generate_summary_ajax/', views.generate_summary_ajax, name='generate_summary_ajax'),
] 