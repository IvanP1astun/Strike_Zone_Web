from django.core.management.base import BaseCommand

from main.user_notifications import send_reminders


class Command(BaseCommand):
    help = (
        'Send a reminder (email / Telegram) to confirmed players of games that start '
        'tomorrow. Safe to run several times a day: every game is reminded once. '
        'Run it daily, e.g. from cron.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=1,
            help='how many days before the game to remind (default: 1)',
        )

    def handle(self, *args, **options):
        reminded = send_reminders(days_ahead=options['days'])
        self.stdout.write('Reminders sent: %d' % reminded)
