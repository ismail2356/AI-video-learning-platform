from django.db import models
from django.contrib.auth.models import User
from videos.models import Video

class Quiz(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.title} ({self.video.title})"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, default='multiple_choice')

    def __str__(self):
        return self.question_text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.answer_text

class UserQuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    answers_json = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.score}"
