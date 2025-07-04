from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from videos.models import Video
from .models import TranscriptSegment
import whisper
import os

# Create your views here.

@login_required
def generate_transcript(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user)
    
    try:
        # Whisper modelini yükle
        model = whisper.load_model("base")
        
        # Videodan ses dosyasını çıkar
        video_path = video.file.path
        audio_path = os.path.splitext(video_path)[0] + ".mp3"
        
        # Video dosyasından ses çıkar
        import moviepy.editor as mp
        video_clip = mp.VideoFileClip(video_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(audio_path)
        audio_clip.close()
        video_clip.close()
        
        # Whisper ile transkript oluştur
        result = model.transcribe(audio_path)
        
        # Mevcut transkriptleri temizle
        TranscriptSegment.objects.filter(video=video).delete()
        
        # Yeni segmentleri kaydet
        for segment in result["segments"]:
            TranscriptSegment.objects.create(
                video=video,
                start_time=segment["start"],
                end_time=segment["end"],
                text=segment["text"].strip()
            )
        
        # Geçici ses dosyasını sil
        os.remove(audio_path)
        
        messages.success(request, 'Transkript başarıyla oluşturuldu.')
        return redirect('videos:video_detail', video_id=video.id)
        
    except Exception as e:
        messages.error(request, f'Transkript oluşturulurken bir hata oluştu: {str(e)}')
        return redirect('videos:video_detail', video_id=video.id)

@login_required
def get_transcript(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user)
    segments = TranscriptSegment.objects.filter(video=video).order_by('start_time')
    
    transcript_data = [{
        'start_time': segment.start_time,
        'end_time': segment.end_time,
        'text': segment.text,
        'time_display': segment.get_time_display()
    } for segment in segments]
    
    return JsonResponse({'segments': transcript_data})
