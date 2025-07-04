from django.db import models
from videos.models import Video
from django.utils import timezone

# Create your models here.

class TranscriptSegment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='transcript_segments')
    start_time = models.FloatField(verbose_name='Başlangıç Zamanı (saniye)')
    end_time = models.FloatField(verbose_name='Bitiş Zamanı (saniye)')
    text = models.TextField(verbose_name='Metin')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Oluşturulma Tarihi')

    class Meta:
        verbose_name = 'Transkript Segmenti'
        verbose_name_plural = 'Transkript Segmentleri'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.video.title} - {self.start_time:.2f}s"

    def get_time_display(self):
        """Zaman aralığını saat:dakika:saniye formatında döndürür"""
        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = int(seconds % 60)
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            return f"{minutes:02d}:{seconds:02d}"
        
        return f"{format_time(self.start_time)} - {format_time(self.end_time)}"
