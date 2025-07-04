from django.db import models
from videos.models import Video

class Summary(models.Model):
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='summary')
    short_summary_text = models.TextField()
    detailed_summary_text = models.TextField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary for {self.video.title}"
