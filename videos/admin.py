from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Video

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'duration_formatted', 'thumbnail_preview', 'uploaded_at', 'view_on_site')
    search_fields = ('title', 'user__username', 'description')
    list_filter = ('status', 'uploaded_at', 'user')
    readonly_fields = ('uploaded_at', 'updated_at', 'thumbnail_preview', 'duration_formatted')
    fieldsets = (
        ('Video Bilgileri', {
            'fields': ('title', 'description', 'file', 'thumbnail', 'thumbnail_preview')
        }),
        ('Kullanıcı ve Durum', {
            'fields': ('user', 'status')
        }),
        ('Teknik Detaylar', {
            'fields': ('duration', 'duration_formatted', 'metadata', 'uploaded_at', 'updated_at')
        }),
    )
    
    def duration_formatted(self, obj):
        if obj.duration:
            return obj.get_duration_display()
        return "Belirsiz"
    duration_formatted.short_description = "Süre"
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="100" height="auto" />', obj.thumbnail.url)
        return "Yok"
    thumbnail_preview.short_description = "Küçük Resim Önizleme"
    
    def view_on_site(self, obj):
        url = reverse('videos:detail', kwargs={'pk': obj.pk})
        return format_html('<a href="{}" target="_blank">Videoyu Görüntüle</a>', url)
    view_on_site.short_description = "Site Önizleme"
