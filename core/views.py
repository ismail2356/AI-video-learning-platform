from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from videos.models import Video
from notes.models import Note
from chat.models import ChatMessage
from quizzes.models import UserQuizAttempt
from .models import UserProfile

# Create your views here.

@login_required
def profile(request):
    user = request.user
    stats = {
        'video_count': Video.objects.filter(user=user).count(),
        'note_count': Note.objects.filter(user=user).count(),
        'chat_count': ChatMessage.objects.filter(user=user).count(),
        'quiz_attempt_count': UserQuizAttempt.objects.filter(user=user).count(),
    }
    return render(request, 'core/profile.html', {'user': user, 'stats': stats})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.bio = request.POST.get('bio', '')
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, 'Profil başarıyla güncellendi.')
        return redirect('core:profile')
    return render(request, 'core/edit_profile.html')

# Ana sayfa view'i
def home(request):
    return render(request, 'core/home.html')

# Kayıt işlemi için view
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Otomatik giriş yap
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, f'Hesabınız başarıyla oluşturuldu!')
            return redirect('core:home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
