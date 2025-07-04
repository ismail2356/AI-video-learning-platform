from django.db import models
from django.contrib.auth.models import User
from videos.models import Video

class Note(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    timestamp = models.FloatField()
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.video.title} - {self.timestamp:.2f}"
