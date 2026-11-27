import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

API = 'https://api.telegram.org/bot{token}/{method}'


class Command(BaseCommand):
    help = (
        'Register (or with --delete remove) the Telegram webhook so that players can '
        'connect their Telegram. Needs TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET and '
        'SITE_URL (public https address).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true', help='remove the webhook')

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise CommandError('TELEGRAM_BOT_TOKEN is not set')
        if options['delete']:
            method, payload = 'deleteWebhook', {}
        else:
            if not settings.TELEGRAM_WEBHOOK_SECRET:
                raise CommandError('TELEGRAM_WEBHOOK_SECRET is not set')
            if not settings.SITE_URL.startswith('https://'):
                raise CommandError('SITE_URL must be a public https:// address')
            method = 'setWebhook'
            payload = {
                'url': settings.SITE_URL + reverse('telegram_webhook'),
                'secret_token': settings.TELEGRAM_WEBHOOK_SECRET,
                'allowed_updates': '["message"]',
            }
        try:
            response = requests.post(API.format(token=token, method=method), data=payload, timeout=10)
        except requests.RequestException as error:
            raise CommandError('Telegram request failed: %s' % error)
        if response.status_code != 200:
            raise CommandError('Telegram answered %s: %s' % (response.status_code, response.text))
        self.stdout.write(self.style.SUCCESS('%s: %s' % (method, response.json().get('description', 'ok'))))
