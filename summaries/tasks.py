from celery import shared_task
from videos.models import Video
from summaries.models import Summary
from transcriptions.models import TranscriptSegment
from core.llm_service import gemini_generate

@shared_task
def generate_summary_task(video_id):
    video = Video.objects.get(id=video_id)
    transcript = '\n'.join(TranscriptSegment.objects.filter(video=video).order_by('start_time').values_list('text', flat=True))
    
    # Kısa özet oluştur
    short_prompt = f"Aşağıdaki video transkriptini 3-4 cümleyle özetle:\n{transcript}"
    short_summary = gemini_generate(short_prompt, max_tokens=256)
    
    # Detaylı özet oluştur
    detailed_prompt = f"""Aşağıdaki video transkriptini detaylı bir şekilde özetle. 
    Ana noktaları ve önemli detayları içersin.
    Özet, düzenli paragraflar halinde olmalı ve aşağıdaki formatta döndürülmeli:
    
    1. Video içeriğinin ana teması
    2. Önemli noktalar (madde işaretleri ile)
    3. Detaylı açıklama (paragraflar halinde)
    
    Transkript:
    {transcript}"""
    
    detailed_summary = gemini_generate(detailed_prompt, max_tokens=1024)
    
    Summary.objects.update_or_create(
        video=video,
        defaults={
            'short_summary_text': short_summary,
            'detailed_summary_text': detailed_summary
        }
    )

def generate_summary_direct(video_id):
    """
    Celery kullanmadan doğrudan özet oluşturma işlemini gerçekleştirir
    """
    from videos.models import Video
    from transcriptions.models import TranscriptSegment
    from summaries.models import Summary
    from core.llm_service import gemini_generate
    
    video = Video.objects.get(id=video_id)
    transcript = '\n'.join(TranscriptSegment.objects.filter(video=video).order_by('start_time').values_list('text', flat=True))
    
    # Kısa özet oluştur
    short_prompt = f"Aşağıdaki video transkriptini 3-4 cümleyle özetle:\n{transcript}"
    short_summary = gemini_generate(short_prompt, max_tokens=256)
    
    # Detaylı özet oluştur
    detailed_prompt = f"""Aşağıdaki video transkriptini detaylı bir şekilde özetle. 
    Ana noktaları ve önemli detayları içersin.
    Özet, düzenli paragraflar halinde olmalı ve aşağıdaki formatta döndürülmeli:
    
    1. Video içeriğinin ana teması
    2. Önemli noktalar (madde işaretleri ile)
    3. Detaylı açıklama (paragraflar halinde)
    
    Transkript:
    {transcript}"""
    
    detailed_summary = gemini_generate(detailed_prompt, max_tokens=1024)
    
    # Var olan özeti güncelle veya yeni özet oluştur
    summary, created = Summary.objects.update_or_create(
        video=video,
        defaults={
            'short_summary_text': short_summary,
            'detailed_summary_text': detailed_summary
        }
    )
    
    return summary 