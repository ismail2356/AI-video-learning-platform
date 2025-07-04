from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Flashcard
from videos.models import Video
from transcriptions.models import TranscriptSegment
from core.llm_service import gemini_generate
import re
import logging

# Create your views here.

@login_required
def flashcards_list(request):
    """
    Kullanıcının tüm bilgi kartlarını videolara göre gruplandırılmış şekilde gösterir
    """
    # Kullanıcının videolarını ve her video için bilgi kartı sayısını al
    videos = Video.objects.filter(user=request.user)
    
    videos_data = []
    for video in videos:
        flashcard_count = Flashcard.objects.filter(video=video).count()
        if flashcard_count > 0:  # Sadece bilgi kartı olan videoları göster
            videos_data.append({
                'video': video,
                'flashcard_count': flashcard_count
            })
    
    context = {
        'videos_data': videos_data
    }
    
    return render(request, 'flashcards/flashcards_list.html', context)

@login_required
def create_flashcards(request, video_id):
    """
    Bilgi kartları oluşturma ve düzenleme sayfası
    """
    video = get_object_or_404(Video, id=video_id, user=request.user)
    flashcards = Flashcard.objects.filter(video=video)
    segments = TranscriptSegment.objects.filter(video=video).order_by('start_time')
    
    if request.method == 'POST':
        if 'generate_flashcards' in request.POST:
            # Bilgi kartları oluştur
            try:
                from .tasks import generate_flashcards_direct
                generate_flashcards_direct(video.id)
                messages.success(request, "Bilgi kartları başarıyla oluşturuldu.")
                return redirect('flashcards:create_flashcards', video_id=video.id)
            except Exception as e:
                messages.error(request, f"Bilgi kartları oluşturulurken hata: {str(e)}")
        elif 'add_flashcard' in request.POST:
            # Yeni kart ekle
            question = request.POST.get('question', '')
            answer = request.POST.get('answer', '')
            
            if question and answer:
                # Temiz metinler oluştur
                clean_question = clean_text(question)
                clean_answer = clean_text(answer)
                
                Flashcard.objects.create(
                    video=video,
                    question_text=clean_question,
                    answer_text=clean_answer
                )
                messages.success(request, "Yeni bilgi kartı eklendi.")
                return redirect('flashcards:create_flashcards', video_id=video.id)
            else:
                messages.error(request, "Soru ve cevap alanları boş olamaz.")
    
    context = {
        'video': video,
        'flashcards': flashcards,
        'segments': segments[:10],  # İlk 10 segment
    }
    return render(request, 'flashcards/create_flashcards.html', context)

@login_required
def edit_flashcard(request, flashcard_id):
    """
    Bilgi kartı düzenleme
    """
    flashcard = get_object_or_404(Flashcard, id=flashcard_id, video__user=request.user)
    
    if request.method == 'POST':
        question = request.POST.get('question', '')
        answer = request.POST.get('answer', '')
        
        if question and answer:
            # Temiz metinler oluştur
            clean_question = clean_text(question)
            clean_answer = clean_text(answer)
            
            flashcard.question_text = clean_question
            flashcard.answer_text = clean_answer
            flashcard.save()
            messages.success(request, "Bilgi kartı güncellendi.")
            return redirect('flashcards:create_flashcards', video_id=flashcard.video.id)
        else:
            messages.error(request, "Soru ve cevap alanları boş olamaz.")
    
    context = {
        'flashcard': flashcard,
        'video': flashcard.video
    }
    return render(request, 'flashcards/edit_flashcard.html', context)

@login_required
def delete_flashcard(request, flashcard_id):
    """
    Bilgi kartı silme
    """
    flashcard = get_object_or_404(Flashcard, id=flashcard_id, video__user=request.user)
    video_id = flashcard.video.id
    
    if request.method == 'POST':
        flashcard.delete()
        messages.success(request, "Bilgi kartı silindi.")
    
    return redirect('flashcards:create_flashcards', video_id=video_id)

@require_POST
@login_required
def generate_flashcards_ajax(request, video_id):
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
    
    llm_response = gemini_generate(prompt, max_tokens=1024)
    
    # Eski flashcard'ları sil
    Flashcard.objects.filter(video=video).delete()
    
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
                # HTML etiketlerini ve gereksiz karakterleri temizle
                clean_question = clean_text(current_question)
                clean_answer = clean_text(current_answer)
                
                card = Flashcard.objects.create(
                    video=video,
                    question_text=clean_question,
                    answer_text=clean_answer
                )
                flashcards.append({'question': card.question_text, 'answer': card.answer_text})
            
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
        # HTML etiketlerini ve gereksiz karakterleri temizle
        clean_question = clean_text(current_question)
        clean_answer = clean_text(current_answer)
        
        card = Flashcard.objects.create(
            video=video,
            question_text=clean_question,
            answer_text=clean_answer
        )
        flashcards.append({'question': card.question_text, 'answer': card.answer_text})
    
    return JsonResponse({'flashcards': flashcards})

@login_required
def clean_flashcards(request, video_id):
    """
    Belirli bir videoya ait bilgi kartlarını siler
    """
    video = get_object_or_404(Video, id=video_id, user=request.user)
    
    try:
        # Kartları say
        total_cards = Flashcard.objects.filter(video=video).count()
        
        # Kartları sil
        deleted_count = Flashcard.objects.filter(video=video).delete()[0]
        
        if deleted_count > 0:
            messages.success(request, f"{deleted_count} bilgi kartı başarıyla silindi.")
        else:
            messages.info(request, "Silinecek bilgi kartı bulunamadı.")
            
    except Exception as e:
        messages.error(request, f"Kartlar silinirken hata oluştu: {str(e)}")
    
    return redirect('flashcards:create_flashcards', video_id=video_id)

def clean_text(text):
    """
    Metindeki HTML etiketlerini ve gereksiz karakterleri temizler
    """
    if not text:
        return ""
    
    # Önce HTML etiketlerini temizle (daha kapsamlı regex)
    text = re.sub(r'<[^>]*>', '', text)
    
    # <br /> ve benzeri etiketleri boşlukla değiştir
    text = text.replace('<br />', ' ')
    text = text.replace('<br/>', ' ')
    text = text.replace('<br>', ' ')
    text = text.replace('&nbsp;', ' ')  # HTML boşluk karakteri
    text = text.replace('&lt;', '<')    # HTML < karakteri
    text = text.replace('&gt;', '>')    # HTML > karakteri
    text = text.replace('&amp;', '&')   # HTML & karakteri
    text = text.replace('&quot;', '"')  # HTML " karakteri
    
    # Yıldız işaretlerini temizle (daha kapsamlı regex)
    text = re.sub(r'\*+', '', text)  # Birden fazla yıldızı temizle
    text = re.sub(r'\*\s*\*', '', text)  # Arada boşluk olan yıldızları temizle
    text = re.sub(r'\s*\*\s*', ' ', text)  # Boşluk-yıldız-boşluk kombinasyonlarını düzelt
    
    # Markdown biçimlendirmesini temizle
    text = re.sub(r'#{1,6}\s+', '', text)  # Başlıkları temizle
    text = re.sub(r'`{1,3}', '', text)     # Kod bloklarını temizle
    text = re.sub(r'>{1,}', '', text)      # Alıntıları temizle
    
    # "Bilgi Kartı X" ifadelerini temizle
    text = re.sub(r'Bilgi Kartı\s*\d*\s*', '', text)
    text = re.sub(r'Kart\s*\d+\s*[:]*', '', text)
    
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    
    # Başlangıç ve sondaki boşlukları temizle
    text = text.strip()
    
    return text

@login_required
def fix_all_flashcards(request):
    """
    Sistemdeki tüm bilgi kartlarını siler
    """
    if not request.user.is_staff:
        messages.error(request, "Bu işlemi yapmaya yetkiniz yok.")
        return redirect('flashcards:flashcards_list')
    
    logger = logging.getLogger(__name__)
    
    try:
        # Tüm kartları say
        total_cards = Flashcard.objects.count()
        logger.info(f"Toplam {total_cards} kart silme işlemi başlatıldı")
        
        # Tüm kartları sil
        deleted_count = Flashcard.objects.all().delete()[0]
        
        logger.info(f"Kart silme işlemi tamamlandı. Silinen: {deleted_count}")
        
        if deleted_count > 0:
            messages.success(request, f"Toplam {deleted_count} bilgi kartı başarıyla silindi.")
        else:
            messages.info(request, "Silinecek bilgi kartı bulunamadı.")
    
    except Exception as e:
        logger.error(f"Kart silme işlemi sırasında hata: {str(e)}")
        messages.error(request, f"Kartlar silinirken hata oluştu: {str(e)}")
    
    return redirect('flashcards:flashcards_list')
