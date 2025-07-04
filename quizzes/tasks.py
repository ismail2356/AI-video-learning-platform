from celery import shared_task
from videos.models import Video
from quizzes.models import Quiz, Question, Answer
from transcriptions.models import TranscriptSegment
from core.llm_service import gemini_generate

@shared_task
def generate_quiz_task(video_id):
    video = Video.objects.get(id=video_id)
    transcript = '\n'.join(TranscriptSegment.objects.filter(video=video).order_by('start_time').values_list('text', flat=True))
    prompt = f"Aşağıdaki transkriptten 2 adet çoktan seçmeli soru oluştur. Her soru için 2 şık ve doğru cevabı belirt.\nFormat: Soru: ...\nA) ...\nB) ...\nDoğru: ...\nTranskript:\n{transcript}"
    llm_response = gemini_generate(prompt, max_tokens=512)
    quiz = Quiz.objects.create(video=video, title='Otomatik Test')
    # Basit ayrıştırma
    for block in llm_response.split('Soru:')[1:]:
        lines = block.strip().split('\n')
        q_text = lines[0]
        a_text = lines[1][3:] if len(lines) > 1 and lines[1].startswith('A)') else ''
        b_text = lines[2][3:] if len(lines) > 2 and lines[2].startswith('B)') else ''
        correct = lines[3][7:].strip() if len(lines) > 3 and lines[3].startswith('Doğru:') else ''
        q = Question.objects.create(quiz=quiz, question_text=q_text)
        Answer.objects.create(question=q, answer_text=a_text, is_correct=(correct == 'A'))
        Answer.objects.create(question=q, answer_text=b_text, is_correct=(correct == 'B'))

def generate_quiz_direct(video_id):
    """
    Celery kullanmadan doğrudan quiz oluşturma işlemini gerçekleştirir
    """
    from videos.models import Video
    from quizzes.models import Quiz, Question, Answer
    from transcriptions.models import TranscriptSegment
    from core.llm_service import gemini_generate
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        video = Video.objects.get(id=video_id)
        transcript = '\n'.join(TranscriptSegment.objects.filter(video=video).order_by('start_time').values_list('text', flat=True))
        
        logger.info(f"Video ID:{video_id} için test oluşturuluyor...")
        
        # Daha kapsamlı ve profesyonel bir prompt
        prompt = f"""Aşağıdaki video transkriptine göre profesyonel bir çoktan seçmeli test oluştur.
Test, video içeriğindeki önemli bilgileri ölçmeye yönelik olmalıdır.

Lütfen aşağıdaki kurallara uygun bir test oluştur:
1. Test için anlamlı ve açıklayıcı bir başlık belirle.
2. En az 5 soru oluştur.
3. Her soru için 4 şık olmalı ve sadece bir tanesi doğru olmalıdır.
4. Sorular video içeriğiyle doğrudan ilişkili olmalıdır.
5. Sorular farklı zorluk seviyelerinde olmalı (kolay, orta ve zor).
6. Doğru cevaplar açık ve net olmalı, yanıltıcı olmamalıdır.
7. Yanlış cevaplar mantıklı ve inandırıcı olmalı, ancak açıkça yanlış olmalıdır.

Yanıtı aşağıdaki JSON formatında döndür:
{{
  "title": "Test başlığı",
  "questions": [
    {{
      "question": "Soru metni",
      "answers": [
        {{"text": "Doğru cevap", "is_correct": true}},
        {{"text": "Yanlış cevap 1", "is_correct": false}},
        {{"text": "Yanlış cevap 2", "is_correct": false}},
        {{"text": "Yanlış cevap 3", "is_correct": false}}
      ]
    }},
    // Diğer sorular...
  ]
}}

SADECE JSON formatında yanıt ver, başka açıklama ekleme.

Transkript:
{transcript}
"""
        
        llm_response = gemini_generate(prompt, max_tokens=2048)
        
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
            
            logger.info("Test verisi başarıyla ayrıştırıldı")
            
            # Eski quiz'leri sil
            deleted_count = Quiz.objects.filter(video=video).delete()[0]
            logger.info(f"{deleted_count} eski test silindi")
            
            # Yeni quiz oluştur
            quiz = Quiz.objects.create(
                video=video,
                title=quiz_data.get('title', f"{video.title} - Test")
            )
            logger.info(f"Yeni test oluşturuldu: {quiz.title}")
            
            # Soruları ekle
            question_count = 0
            for q_data in quiz_data.get('questions', []):
                question = Question.objects.create(
                    quiz=quiz,
                    question_text=q_data.get('question', '')
                )
                
                # Cevapları ekle
                answer_count = 0
                for a_data in q_data.get('answers', []):
                    Answer.objects.create(
                        question=question,
                        answer_text=a_data.get('text', ''),
                        is_correct=a_data.get('is_correct', False)
                    )
                    answer_count += 1
                
                question_count += 1
                logger.info(f"Soru {question_count} eklendi, {answer_count} cevap içeriyor")
            
            logger.info(f"Test oluşturma tamamlandı. Toplam {question_count} soru eklendi.")
            return quiz
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON ayrıştırma hatası: {str(e)}")
            logger.error(f"Ham yanıt: {llm_response[:500]}...")
            
            # JSON ayrıştırma hatası durumunda basit bir quiz oluştur
            quiz = Quiz.objects.create(
                video=video,
                title=f"{video.title} - Test"
            )
            
            question = Question.objects.create(
                quiz=quiz,
                question_text="Video içeriği hakkında soru"
            )
            
            Answer.objects.create(question=question, answer_text="Doğru cevap", is_correct=True)
            Answer.objects.create(question=question, answer_text="Yanlış cevap 1", is_correct=False)
            Answer.objects.create(question=question, answer_text="Yanlış cevap 2", is_correct=False)
            Answer.objects.create(question=question, answer_text="Yanlış cevap 3", is_correct=False)
            
            logger.info("Yedek test oluşturuldu")
            return quiz
            
    except Exception as e:
        logger.error(f"Test oluşturma sırasında hata: {str(e)}")
        raise e 