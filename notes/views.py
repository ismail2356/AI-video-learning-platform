from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Note
from videos.models import Video

# Create your views here.

@login_required
def notes_list(request):
    notes = Note.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notes/notes_list.html', {'notes': notes})

@require_POST
@login_required
def add_note_ajax(request, video_id):
    video = Video.objects.get(id=video_id)
    note_text = request.POST.get('note_text')
    timestamp = request.POST.get('timestamp') or 0
    note = Note.objects.create(
        video=video,
        user=request.user,
        note_text=note_text,
        timestamp=timestamp
    )
    return JsonResponse({
        'user': note.user.username,
        'timestamp': f"{note.timestamp:.2f}",
        'note_text': note.note_text,
        'created_at': note.created_at.strftime('%Y-%m-%d %H:%M')
    })
