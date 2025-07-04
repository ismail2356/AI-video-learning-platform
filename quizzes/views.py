from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Quiz, Question, Answer, UserQuizAttempt
from videos.models import Video
from transcriptions.models import TranscriptSegment
from core.llm_service import gemini_generate
import json

# Create your views here.

@login_required
def quizzes_list(request):
    # Kullanıcının denediği quizleri al
    user_attempts = UserQuizAttempt.objects.filter(user=request.user).select_related('quiz__video')
    
    # Tüm quizleri al - id'ye göre sırala (en yeniden en eskiye)
    all_quizzes = Quiz.objects.select_related('video').filter(video__user=request.user).order_by('-id')
    
    # Kullanıcının henüz denemediği quizleri bul
    attempted_quiz_ids = user_attempts.values_list('quiz_id', flat=True)
    unattempted_quizzes = all_quizzes.exclude(id__in=attempted_quiz_ids)
    
    context = {
        'user_attempts': user_attempts,
        'unattempted_quizzes': unattempted_quizzes
    }
    
    return render(request, 'quizzes/quizzes_list.html', context)

@login_required
def create_quiz(request, video_id):
    """
    Test oluşturma sayfası - sadece otomatik test oluşturma işlevini içerir
    """
    video = get_object_or_404(Video, id=video_id, user=request.user)
    quizzes = Quiz.objects.filter(video=video)
    segments = TranscriptSegment.objects.filter(video=video).order_by('start_time')
    
    if request.method == 'POST':
        if 'generate_quiz' in request.POST:
            # Test oluştur
            try:
                from .tasks import generate_quiz_direct
                generate_quiz_direct(video.id)
                messages.success(request, "Test başarıyla oluşturuldu.")
                # Oluşturulduğunda doğrudan teste yönlendir
                quiz = Quiz.objects.filter(video=video).first()
                if quiz:
                    return redirect('quizzes:take_quiz', quiz_id=quiz.id)
                return redirect('quizzes:create_quiz', video_id=video.id)
            except Exception as e:
                messages.error(request, f"Test oluşturulurken hata: {str(e)}")
    
    context = {
        'video': video,
        'quizzes': quizzes,
        'segments': segments[:10],  # İlk 10 segment
    }
    return render(request, 'quizzes/create_quiz.html', context)

@login_required
def delete_quiz(request, quiz_id):
    """
    Test silme
    """
    quiz = get_object_or_404(Quiz, id=quiz_id, video__user=request.user)
    video_id = quiz.video.id
    
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, "Test silindi.")
    
    return redirect('quizzes:create_quiz', video_id=video_id)

@require_POST
@login_required
def generate_quiz_ajax(request, video_id):
    video = Video.objects.get(id=video_id)
    transcript = '\n'.join(TranscriptSegment.objects.filter(video=video).order_by('start_time').values_list('text', flat=True))
    
    prompt = f"""Aşağıdaki video transkriptine göre 5 soruluk bir test oluştur.
Her soru için 4 şık olsun ve sadece bir tanesi doğru olsun.
Yanıtı JSON formatında döndür. Markdown formatını kullanabilirsin:

{{
  "title": "Video içeriği ile ilgili anlamlı bir test başlığı",
  "questions": [
    {{
      "question": "Soru metni (markdown formatında yazabilirsin)",
      "answers": [
        {{"text": "Doğru cevap", "is_correct": true}},
        {{"text": "Yanlış cevap 1", "is_correct": false}},
        {{"text": "Yanlış cevap 2", "is_correct": false}},
        {{"text": "Yanlış cevap 3", "is_correct": false}}
      ]
    }}
  ]
}}

Sorular video içeriğiyle doğrudan ilgili ve öğrenmeyi pekiştirici olmalıdır.
Cevap şıkları mantıklı ve ayırt edici olmalıdır.
SADECE JSON formatında yanıt ver, başka açıklama ekleme.

Transkript:
{transcript}
"""
    
    llm_response = gemini_generate(prompt, max_tokens=1024)
    
    try:
        # JSON yanıtı ayrıştır
        # Bazen Gemini API cevabın başına veya sonuna ek metin ekleyebiliyor
        # Bu yüzden JSON kısmını çıkarmaya çalışalım
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_response = llm_response[json_start:json_end]
            quiz_data = json.loads(json_response)
        else:
            quiz_data = json.loads(llm_response)
        
        # Eski quiz'leri sil
        Quiz.objects.filter(video=video).delete()
        
        # Yeni quiz oluştur
        quiz = Quiz.objects.create(
            video=video,
            title=quiz_data.get('title', f"{video.title} Quiz")
        )
        
        questions_data = []
        
        # Soruları ekle
        for q_data in quiz_data.get('questions', []):
            question = Question.objects.create(
                quiz=quiz,
                question_text=q_data.get('question', '')
            )
            
            answers_data = []
            
            # Cevapları ekle
            for a_data in q_data.get('answers', []):
                answer = Answer.objects.create(
                    question=question,
                    answer_text=a_data.get('text', ''),
                    is_correct=a_data.get('is_correct', False)
                )
                answers_data.append({
                    'id': answer.id,
                    'text': answer.answer_text,
                    'is_correct': answer.is_correct
                })
            
            questions_data.append({
                'id': question.id,
                'question': question.question_text,
                'answers': answers_data
            })
        
        return JsonResponse({
            'success': True,
            'quiz_id': quiz.id,
            'title': quiz.title,
            'questions': questions_data,
            'take_quiz_url': f"/quizzes/take/{quiz.id}/"
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def take_quiz(request, quiz_id):
    """
    Test çözme sayfası
    """
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz).prefetch_related('answers')
    
    # Soruların rastgele sıralanması için aktif etmek istiyorsanız:
    # from django.db.models import F
    # questions = questions.order_by('?')
    
    context = {
        'quiz': quiz,
        'questions': questions,
    }
    return render(request, 'quizzes/take_quiz.html', context)

@login_required
def submit_quiz(request, quiz_id):
    """
    Test cevaplarını kontrol edip sonuçları kaydet
    """
    if request.method != 'POST':
        return redirect('quizzes:take_quiz', quiz_id=quiz_id)
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz).prefetch_related('answers')
    
    correct_count = 0
    results = []
    
    for question in questions:
        answer_key = f"answer_{question.id}"
        selected_answer_id = request.POST.get(answer_key)
        
        if selected_answer_id:
            selected_answer = get_object_or_404(Answer, id=selected_answer_id)
            is_correct = selected_answer.is_correct
            
            if is_correct:
                correct_count += 1
                
            results.append({
                'question': question,
                'selected_answer': selected_answer,
                'is_correct': is_correct
            })
    
    # Hesaplama
    total_questions = questions.count()
    if total_questions > 0:
        score = int((correct_count / total_questions) * 100)
    else:
        score = 0
    
    # Sonuçları kaydet
    attempt = UserQuizAttempt.objects.create(
        user=request.user,
        quiz=quiz,
        score=score,
        answers_json=json.dumps({str(item['question'].id): str(item['selected_answer'].id) for item in results})
    )
    
    messages.success(request, f"Test tamamlandı! Puanınız: {score}%")
    return redirect('quizzes:quiz_results', attempt_id=attempt.id)

@login_required
def quiz_results(request, attempt_id):
    """
    Test sonuçlarını göster
    """
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id, user=request.user)
    quiz = attempt.quiz
    questions = Question.objects.filter(quiz=quiz).prefetch_related('answers')
    
    # Kullanıcının cevaplarını yükle
    answers_dict = json.loads(attempt.answers_json)
    
    results = []
    correct_count = 0
    
    for question in questions:
        selected_answer_id = answers_dict.get(str(question.id))
        if selected_answer_id:
            selected_answer = get_object_or_404(Answer, id=selected_answer_id)
            is_correct = selected_answer.is_correct
            
            if is_correct:
                correct_count += 1
                
            results.append({
                'question': question,
                'selected_answer': selected_answer,
                'is_correct': is_correct
            })
    
    context = {
        'quiz': quiz,
        'attempt': attempt,
        'results': results,
        'correct_count': correct_count,
        'total_questions': questions.count()
    }
    
    return render(request, 'quizzes/quiz_results.html', context)
