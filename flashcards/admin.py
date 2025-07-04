from django.contrib import admin
from .models import Flashcard

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('video', 'question_text', 'created_at')
    search_fields = ('video__title', 'question_text', 'answer_text')
    list_filter = ('video', 'created_at')
