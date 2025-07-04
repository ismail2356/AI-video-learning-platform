from django.db import models
from django.contrib.auth.models import User

class Video(models.Model):
    STATUS_CHOICES = [
        ('pending', 'İşlem Bekliyor'),
        ('processing', 'İşleniyor'),
        ('ready', 'Hazır'),
        ('transcribed', 'Transkript Edildi'),
        ('failed', 'Hata Oluştu'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, verbose_name='Başlık')
    description = models.TextField(blank=True, null=True, verbose_name='Açıklama')
    file = models.FileField(upload_to='videos/', verbose_name='Video Dosyası')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True, verbose_name='Küçük Resim')
    duration = models.FloatField(null=True, blank=True, verbose_name='Süre (saniye)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Durum')
    metadata = models.JSONField(null=True, blank=True, verbose_name='Meta Veriler')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Yüklenme Tarihi')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Güncellenme Tarihi')

    class Meta:
        verbose_name = 'Video'
        verbose_name_plural = 'Videolar'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def get_duration_display(self):
        """Video süresini saat:dakika:saniye formatında döndürür"""
        if not self.duration:
            return "Belirsiz"
        
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
