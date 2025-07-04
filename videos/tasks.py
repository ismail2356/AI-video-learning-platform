from celery import shared_task
from moviepy.editor import VideoFileClip
from .models import Video
from transcriptions.tasks import transcribe_video_task

@shared_task
def extract_video_metadata_task(video_id):
    try:
        video = Video.objects.get(id=video_id)
        clip = VideoFileClip(video.file.path)
        metadata = {
            'duration': clip.duration,
            'fps': clip.fps,
            'size': clip.size,
            'audio': clip.audio is not None,
        }
        video.metadata = metadata
        video.status = 'ready'
        video.save()
        clip.close()
        transcribe_video_task.delay(video.id)
    except Exception as e:
        video.status = 'failed'
        video.save()
        raise e 