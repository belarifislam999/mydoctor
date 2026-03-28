from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Crée un superutilisateur admin par défaut si aucun n existe'
    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@mydoctor.com', 'Admin1234!')
            self.stdout.write(self.style.SUCCESS('✅ Admin créé : admin / Admin1234!'))
        else:
            self.stdout.write('Admin existe déjà.')
