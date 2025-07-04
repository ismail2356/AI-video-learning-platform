from celery import shared_task
from videos.models import Video
from .models import TranscriptSegment
import whisper
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def transcribe_video_task(video_id):
    video = Video.objects.get(id=video_id)
    try:
        # Model dizinini belirle
        model_dir = os.path.join(settings.BASE_DIR, 'models', 'whisper')
        os.makedirs(model_dir, exist_ok=True)
        
        # Modeli yükle
        logger.info(f"Whisper modeli yükleniyor: {model_dir}")
        model = whisper.load_model('base', download_root=model_dir)
        
        # Video dosyasının var olduğunu kontrol et
        if not os.path.exists(video.file.path):
            raise FileNotFoundError(f"Video dosyası bulunamadı: {video.file.path}")
        
        # Transkripsiyon işlemi
        logger.info(f"Video transkript ediliyor: {video.title}")
        result = model.transcribe(video.file.path, word_timestamps=True)
        
        # Segmentleri işle
        segments = result.get('segments', [])
        transcript_objs = []
        for seg in segments:
            transcript_objs.append(TranscriptSegment(
                video=video,
                start_time=seg['start'],
                end_time=seg['end'],
                text=seg['text']
            ))
        
        # Veritabanına kaydet
        TranscriptSegment.objects.bulk_create(transcript_objs)
        video.status = 'transcribed'
        video.save()
        
        logger.info(f"Video transkript edildi: {video.title}, {len(transcript_objs)} segment")
        
    except Exception as e:
        logger.error(f"Transkripsiyon hatası: {str(e)}", exc_info=True)
        video.status = 'failed'
        video.metadata = video.metadata or {}
        video.metadata['transcription_error'] = str(e)
        video.save()
        raise e

def transcribe_video(video_id):
    """
    Celery kullanmadan doğrudan video transkript işlemini gerçekleştirir
    """
    video = Video.objects.get(id=video_id)
    try:
        # Model dizinini belirle
        model_dir = os.path.join(settings.BASE_DIR, 'models', 'whisper')
        os.makedirs(model_dir, exist_ok=True)
        
        # Modeli yükle
        logger.info(f"Whisper modeli yükleniyor: {model_dir}")
        model = whisper.load_model('base', download_root=model_dir)
        
        # Video dosyasının var olduğunu kontrol et
        if not os.path.exists(video.file.path):
            raise FileNotFoundError(f"Video dosyası bulunamadı: {video.file.path}")
        
        # Transkripsiyon işlemi
        logger.info(f"Video transkript ediliyor: {video.title}")
        result = model.transcribe(video.file.path, word_timestamps=True)
        
        # Segmentleri işle
        segments = result.get('segments', [])
        transcript_objs = []
        for seg in segments:
            transcript_objs.append(TranscriptSegment(
                video=video,
                start_time=seg['start'],
                end_time=seg['end'],
                text=seg['text']
            ))
        
        # Veritabanına kaydet
        TranscriptSegment.objects.bulk_create(transcript_objs)
        video.status = 'transcribed'
        video.save()
        
        logger.info(f"Video transkript edildi: {video.title}, {len(transcript_objs)} segment")
        
    except Exception as e:
        logger.error(f"Transkripsiyon hatası: {str(e)}", exc_info=True)
        video.status = 'failed'
        video.metadata = video.metadata or {}
        video.metadata['transcription_error'] = str(e)
        video.save()
        raise e 