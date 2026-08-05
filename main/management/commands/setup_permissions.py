from django.core.management.base import BaseCommand
from main.models import create_groups


class Command(BaseCommand):
    help = 'Создаёт группы и права для пользователей'

    def handle(self, *args, **options):
        group = create_groups()
        self.stdout.write(
            self.style.SUCCESS(f'✅ Группа "{group.name}" создана с правами!')
        )
        self.stdout.write(self.style.SUCCESS('📋 Права:'))
        for perm in group.permissions.all():
            self.stdout.write(f'  - {perm.name}')
