from django.db import models
from django.contrib.auth.models import User
from videos.models import Video

# Create your models here.

class ChatMessage(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    timestamp = models.FloatField(null=True, blank=True)
    prompt_text = models.TextField()
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.prompt_text[:30]}..."
