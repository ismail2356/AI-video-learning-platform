from django.contrib import admin
from .models import Summary

@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ('video', 'generated_at')
    search_fields = ('video__title', 'short_summary_text', 'detailed_summary_text')
    list_filter = ('generated_at',)
