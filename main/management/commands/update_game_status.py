from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import AirsoftGame


class Command(BaseCommand):
    help = 'Обновляет статусы игр'

    def handle(self, *args, **options):
        games = AirsoftGame.objects.all()
        updated = 0

        for game in games:
            game.update_status()
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f'✅ Обновлено статусов: {updated}')
        )
