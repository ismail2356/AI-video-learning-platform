from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import ChatMessage
from videos.models import Video

# Create your views here.

@require_POST
@login_required
def add_chat_message_ajax(request, video_id):
    video = Video.objects.get(id=video_id)
    prompt = request.POST.get('prompt_text')
    # Basit bir AI yanıtı simülasyonu (ileride Gemini API ile değiştirilecek)
    response = 'AI yanıtı: ' + prompt
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
        'response_text': msg.response_text
    })
