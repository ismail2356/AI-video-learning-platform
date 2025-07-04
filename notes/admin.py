from django.contrib import admin
from .models import Note

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'timestamp', 'created_at', 'updated_at')
    search_fields = ('user__username', 'video__title', 'note_text')
    list_filter = ('video', 'created_at')
