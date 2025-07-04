from django.contrib import admin
from .models import Quiz, Question, Answer, UserQuizAttempt

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1

class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]
    list_display = ('quiz', 'question_text', 'question_type')
    search_fields = ('question_text',)
    list_filter = ('quiz',)

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'video')
    search_fields = ('title', 'video__title')
    list_filter = ('video',)

admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer)
admin.site.register(UserQuizAttempt)
