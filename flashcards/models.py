from django.db import models
from videos.models import Video

class Flashcard(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='flashcards')
    question_text = models.TextField()
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.video.title} - {self.question_text[:30]}..."
