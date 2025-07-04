from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Summary
from videos.models import Video
from transcriptions.models import TranscriptSegment
from core.llm_service import gemini_generate

# Create your views here.

@require_POST
@login_required
def generate_summary_ajax(request, video_id):
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
    
    summary, _ = Summary.objects.update_or_create(
        video=video,
        defaults={
            'short_summary_text': short_summary,
            'detailed_summary_text': detailed_summary
        }
    )
    return JsonResponse({
        'short_summary': summary.short_summary_text,
        'detailed_summary': summary.detailed_summary_text
    })
