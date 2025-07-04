from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Profil nesnesi olmayan kullanıcılar için profil nesneleri oluşturur'

    def handle(self, *args, **options):
        users_without_profile = []
        for user in User.objects.all():
            try:
                # Profil var mı kontrol et
                user.profile
            except User.profile.RelatedObjectDoesNotExist:
                # Profil yoksa listeye ekle
                users_without_profile.append(user)
        
        # Eksik profilleri oluştur
        for user in users_without_profile:
            UserProfile.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f'"{user.username}" için profil oluşturuldu'))
        
        if not users_without_profile:
            self.stdout.write(self.style.SUCCESS('Tüm kullanıcıların profilleri zaten var'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Toplam {len(users_without_profile)} kullanıcı için profil oluşturuldu')) 