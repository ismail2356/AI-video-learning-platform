from django.contrib import admin
from .models import TranscriptSegment

@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = ('video', 'start_time', 'end_time', 'text')
    search_fields = ('video__title', 'text')
    list_filter = ('video',)
