from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import VideoUploadForm
from .models import Video
from .tasks import extract_video_metadata_task
from transcriptions.models import TranscriptSegment
from summaries.models import Summary
from flashcards.models import Flashcard
from quizzes.models import Quiz
from chat.models import ChatMessage
from notes.models import Note
from django.views.decorators.http import require_POST
from summaries.tasks import generate_summary_task
from flashcards.tasks import generate_flashcards_task
from quizzes.tasks import generate_quiz_task
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import moviepy.editor as mp
import os
from django.conf import settings
from transcriptions.tasks import transcribe_video_task
from core.llm_service import gemini_generate
import logging

# Create your views here.

@login_required
def video_list(request):
    videos = Video.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'videos/video_list.html', {'videos': videos})

@login_required
def video_upload(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.user = request.user
            video.status = 'processing'
            video.save()

            try:
                # Video meta verilerini çıkar
                video_path = video.file.path
                video_clip = mp.VideoFileClip(video_path)
                
                # Meta verileri kaydet
                video.duration = video_clip.duration
                video.metadata = {
                    'fps': video_clip.fps,
                    'size': video_clip.size,
                    'duration': video_clip.duration
                }
                
                # Thumbnail oluştur
                thumbnail_time = min(1.0, video_clip.duration)
                thumbnail_frame = video_clip.get_frame(thumbnail_time)
                
                # Thumbnail dizinini oluştur
                thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
                if not os.path.exists(thumbnail_dir):
                    os.makedirs(thumbnail_dir)
                
                # Thumbnail dosyasının tam yolunu oluştur
                thumbnail_filename = f'{video.id}_thumb.jpg'
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                
                # Thumbnail'i kaydet
                mp.ImageClip(thumbnail_frame).save_frame(thumbnail_path)
                
                # Video nesnesini güncelle
                video_clip.close()
                
                video.status = 'ready'
                video.thumbnail = f'thumbnails/{thumbnail_filename}'  # Veritabanında göreceli yolu kaydet
                video.save()
                
                # Transkripsiyon işlemini doğrudan çağır (Celery kullanmadan)
                try:
                    from transcriptions.tasks import transcribe_video
                    messages.success(request, 'Video başarıyla yüklendi. Transkript oluşturuluyor...')
                    # Asenkron işlem yerine doğrudan çağır
                    transcribe_video(video.id)
                except Exception as e:
                    messages.warning(request, f'Video yüklendi ancak transkript oluşturulurken hata: {str(e)}')
                
                return redirect('videos:video_list')
                
            except Exception as e:
                video.status = 'failed'
                video.metadata = {'error': str(e)}
                video.save()
                messages.error(request, f'Video işlenirken bir hata oluştu: {str(e)}')
                return redirect('videos:video_list')
    else:
        form = VideoUploadForm()
    
    return render(request, 'videos/video_upload.html', {'form': form})

@login_required
def video_detail(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user)
    segments = TranscriptSegment.objects.filter(video=video).order_by('start_time')
    summary = getattr(video, 'summary', None)
    
    # Kartları ve testleri getir
    flashcards = Flashcard.objects.filter(video=video)
    quizzes = Quiz.objects.filter(video=video)
    
    # Test başlatma parametresi kontrol et
    start_quiz_id = request.GET.get('start_quiz')
    if start_quiz_id:
        try:
            quiz = Quiz.objects.get(id=start_quiz_id, video=video)
            return redirect('quizzes:take_quiz', quiz_id=quiz.id)
        except Quiz.DoesNotExist:
            messages.error(request, "Belirtilen test bulunamadı.")
    
    chat_messages = ChatMessage.objects.filter(video=video).order_by('created_at')
    notes = Note.objects.filter(video=video).order_by('timestamp')
    return render(request, 'videos/video_detail.html', {
        'video': video,
        'segments': segments,
        'summary': summary,
        'flashcards': flashcards,
        'quizzes': quizzes,
        'chat_messages': chat_messages,
        'notes': notes,
    })

@login_required
@require_POST
def add_chat_message(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    prompt = request.POST.get('prompt_text')
    
    # Gemini API ile yanıt oluştur
    segments = TranscriptSegment.objects.filter(video=video).order_by('start_time')
    context = "\n".join([f"{seg.start_time:.2f}-{seg.end_time:.2f}: {seg.text}" for seg in segments[:10]])
    
    # Prompt oluştur
    ai_prompt = f"""Video hakkındaki bilgilerle kullanıcının sorusunu yanıtla.

Video başlığı: {video.title}
Video açıklaması: {video.description or 'Açıklama yok'}
Transkriptten parça:
{context}

Kullanıcı sorusu: {prompt}

Yanıtın kısa ve bilgilendirici olsun."""
    
    # Gemini'den yanıt al
    try:
        response = gemini_generate(ai_prompt, max_tokens=512)
    except Exception as e:
        response = f"Üzgünüm, yanıt oluşturulurken bir hata oluştu: {str(e)}"
    
    # Mesajı kaydet
    chat_message = ChatMessage.objects.create(
        video=video,
        user=request.user,
        prompt_text=prompt,
        response_text=response,
        timestamp=request.POST.get('timestamp') or None
    )
    
    return redirect('videos:video_detail', video_id=video_id)

@login_required
@require_POST
def add_note(request, video_id):
    video = Video.objects.get(id=video_id)
    note_text = request.POST.get('note_text')
    timestamp = request.POST.get('timestamp') or 0
    Note.objects.create(
        video=video,
        user=request.user,
        note_text=note_text,
        timestamp=timestamp
    )
    return redirect('video_detail', video_id=video_id)

@login_required
@require_POST
def generate_summary(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user)
    try:
        from summaries.tasks import generate_summary_direct
        generate_summary_direct(video_id)
        messages.success(request, 'Özet oluşturuldu.')
    except Exception as e:
        messages.error(request, f'Özet oluşturulurken hata: {str(e)}')
    return redirect('videos:video_detail', video_id=video_id)

@login_required
@require_POST
def generate_flashcards(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user)
    try:
        from flashcards.tasks import generate_flashcards_direct
        generate_flashcards_direct(video_id)
        messages.success(request, 'Bilgi kartları oluşturuldu.')
    except Exception as e:
        messages.error(request, f'Bilgi kartları oluşturulurken hata: {str(e)}')
    return redirect('videos:video_detail', video_id=video_id)

@login_required
@require_POST
def generate_quiz(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user)
    try:
        from quizzes.tasks import generate_quiz_direct
        generate_quiz_direct(video_id)
        messages.success(request, 'Test oluşturuldu.')
    except Exception as e:
        messages.error(request, f'Test oluşturulurken hata: {str(e)}')
    return redirect('videos:video_detail', video_id=video_id)

@login_required
@require_POST
def add_chat_message_ajax(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    prompt = request.POST.get('prompt_text')
    
    # Gemini API ile yanıt oluştur
    segments = TranscriptSegment.objects.filter(video=video).order_by('start_time')
    context = "\n".join([f"{seg.start_time:.2f}-{seg.end_time:.2f}: {seg.text}" for seg in segments[:10]])
    
    # Prompt oluştur
    ai_prompt = f"""Video hakkındaki bilgilerle kullanıcının sorusunu yanıtla.

Video başlığı: {video.title}
Video açıklaması: {video.description or 'Açıklama yok'}
Transkriptten parça:
{context}

Kullanıcı sorusu: {prompt}

Yanıtın kısa ve bilgilendirici olsun."""
    
    # Gemini'den yanıt al
    rate_limit_error = False
    try:
        response = gemini_generate(ai_prompt, max_tokens=512)
    except Exception as e:
        error_message = str(e)
        rate_limit_error = "429" in error_message
        
        if rate_limit_error:
            response = "API hizmet sınırına ulaşıldı. Şu anda sistemimiz çok yoğun. Lütfen birkaç dakika sonra tekrar deneyin."
        else:
            response = f"Üzgünüm, yanıt oluşturulurken bir hata oluştu: {error_message}"
        
        # Hatayı logla
        logger = logging.getLogger(__name__)
        logger.error(f"Chat yanıtı oluşturma hatası: {error_message}")
    
    # Mesajı kaydet
    msg = ChatMessage.objects.create(
        video=video,
        user=request.user,
        prompt_text=prompt,
        response_text=response,
        timestamp=request.POST.get('timestamp') or None
    )
    
    return JsonResponse({
        'user': msg.user.username,
        'created_at': msg.created_at.strftime('%H:%M'),
        'prompt_text': msg.prompt_text,
        'response_text': msg.response_text,
        'error': rate_limit_error
    })

@login_required
@require_POST
def add_note_ajax(request, video_id):
    try:
        video = get_object_or_404(Video, id=video_id)
        note_text = request.POST.get('note_text')
        timestamp = request.POST.get('timestamp') or 0
        
        if not note_text:
            return JsonResponse({'error': 'Not metni boş olamaz'}, status=400)
            
        note = Note.objects.create(
            video=video,
            user=request.user,
            note_text=note_text,
            timestamp=float(timestamp)
        )
        
        return JsonResponse({
            'success': True,
            'user': note.user.username,
            'timestamp': f"{float(note.timestamp):.2f}",
            'note_text': note.note_text,
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M')
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Not ekleme hatası: {str(e)}")
        return JsonResponse({'error': f'Not eklenirken bir hata oluştu: {str(e)}'}, status=500)

@login_required
@require_POST
def delete_video(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user)
    video_title = video.title
    
    try:
        # Video dosyasını ve bağlantılı tüm verileri sil
        if video.thumbnail:
            if os.path.exists(video.thumbnail.path):
                os.remove(video.thumbnail.path)
        
        if video.file:
            if os.path.exists(video.file.path):
                os.remove(video.file.path)
                
        # Video kaydını veritabanından sil
        video.delete()
        messages.success(request, f'"{video_title}" başarıyla silindi.')
    except Exception as e:
        messages.error(request, f'Video silinirken bir hata oluştu: {str(e)}')
    
    return redirect('videos:video_list')
