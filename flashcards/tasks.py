import logging
from celery import shared_task
from videos.models import Video
from flashcards.models import Flashcard
from transcriptions.models import TranscriptSegment
from core.llm_service import gemini_generate
from flashcards.views import clean_text  # clean_text fonksiyonunu import et

@shared_task
def generate_flashcards_task(video_id):
    video = Video.objects.get(id=video_id)
    transcript = '\n'.join(TranscriptSegment.objects.filter(video=video).order_by('start_time').values_list('text', flat=True))
    prompt = f"Aşağıdaki transkriptten 3 adet Soru/Cevap formatında bilgi kartı oluştur.\nFormat: Soru: ... Cevap: ...\nTranskript:\n{transcript}"
    llm_response = gemini_generate(prompt, max_tokens=512)
    # Basit ayrıştırma
    for pair in llm_response.split('Soru:')[1:]:
        q, a = pair.split('Cevap:') if 'Cevap:' in pair else (pair, '')
        Flashcard.objects.create(
            video=video,
            question_text=q.strip(),
            answer_text=a.strip()
        )

def generate_flashcards_direct(video_id):
    """
    Celery kullanmadan doğrudan flashcard oluşturma işlemini gerçekleştirir
    """
    logger = logging.getLogger(__name__)
    
    try:
        video = Video.objects.get(id=video_id)
        transcript = '\n'.join(TranscriptSegment.objects.filter(video=video).order_by('start_time').values_list('text', flat=True))
        
        prompt = f"""Aşağıdaki video transkriptine göre 5 adet bilgi kartı oluştur.
Her bilgi kartı için bir soru ve cevap içermelidir.
Yanıtı aşağıdaki formatta döndür (markdown formatında):

Soru 1: [Soru metni]
Cevap 1: [Cevap metni]

Soru 2: [Soru metni]
Cevap 2: [Cevap metni]

(ve diğerleri...)

Sorular açık ve net olmalı, cevaplar ise kapsamlı ve bilgilendirici olmalıdır.
Markdown formatını kullanabilirsin (başlıklar, listeler, vb.).
HTML etiketleri (<br>, <b>, <strong> vb.) KULLANMA, sadece düz metin ve markdown kullan.
Yıldız (*) işaretlerini kullanma.

Transkript:
{transcript}
"""
        
        logger.info(f"Video ID:{video_id} için bilgi kartları oluşturuluyor...")
        llm_response = gemini_generate(prompt, max_tokens=1024)
        
        # Eski flashcard'ları sil
        deleted_count = Flashcard.objects.filter(video=video).delete()[0]
        logger.info(f"{deleted_count} eski bilgi kartı silindi")
        
        # Daha iyi ayrıştırma
        flashcards = []
        current_question = None
        current_answer = None
        
        for line in llm_response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Soru '):
                # Eğer önceki soru/cevap varsa kaydet
                if current_question and current_answer:
                    try:
                        # HTML etiketlerini ve gereksiz karakterleri temizle
                        clean_question = clean_text(current_question)
                        clean_answer = clean_text(current_answer)
                        
                        card = Flashcard.objects.create(
                            video=video,
                            question_text=clean_question,
                            answer_text=clean_answer
                        )
                        flashcards.append(card)
                        logger.info(f"Bilgi kartı oluşturuldu: {clean_question[:30]}...")
                    except Exception as e:
                        logger.error(f"Bilgi kartı oluşturma hatası: {str(e)}")
                
                # Yeni soru başlat
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_question = parts[1].strip()
                    current_answer = None
            
            elif line.startswith('Cevap '):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_answer = parts[1].strip()
        
        # Son soruyu da ekle
        if current_question and current_answer:
            try:
                # HTML etiketlerini ve gereksiz karakterleri temizle
                clean_question = clean_text(current_question)
                clean_answer = clean_text(current_answer)
                
                card = Flashcard.objects.create(
                    video=video,
                    question_text=clean_question,
                    answer_text=clean_answer
                )
                flashcards.append(card)
                logger.info(f"Son bilgi kartı oluşturuldu: {clean_question[:30]}...")
            except Exception as e:
                logger.error(f"Bilgi kartı oluşturma hatası: {str(e)}")
        
        logger.info(f"Toplam {len(flashcards)} bilgi kartı oluşturuldu")
        return flashcards
        
    except Exception as e:
        logger.error(f"Video {video_id} için bilgi kartları oluşturulurken genel hata: {str(e)}")
        raise e 