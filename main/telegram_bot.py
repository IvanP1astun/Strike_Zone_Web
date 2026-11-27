"""Telegram bot webhook: links a Telegram chat to a site account.

The profile page creates a one-time code and shows the link
https://t.me/<bot>?start=<code>. Telegram sends "/start <code>" to the webhook
and the chat is stored in the profile. "/stop" disconnects it.
"""
import logging

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _

from .models import Profile
from .notifications import send_telegram_to

logger = logging.getLogger(__name__)


def _reply(chat_id, text, language=None):
    send_telegram_to(chat_id, text)


def _in_language(language, func):
    with translation.override(language or settings.LANGUAGE_CODE):
        return func()


def handle_update(update):
    """Process one Telegram update (a dict). Unknown updates are ignored."""
    message = (update or {}).get('message') or {}
    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    text = (message.get('text') or '').strip()
    if not chat_id or chat.get('type') != 'private' or not text.startswith('/'):
        return

    command, _sep, argument = text.partition(' ')
    command = command.split('@')[0].lower()
    argument = argument.strip()

    if command == '/start' and argument:
        _link(chat_id, argument)
    elif command == '/start':
        _reply(chat_id, _in_language(None, lambda: _(
            'Привет! Чтобы подключить уведомления, нажмите «Подключить Telegram» '
            'в личном кабинете на сайте.'
        )))
    elif command == '/stop':
        _unlink(chat_id)


def _link(chat_id, token):
    profile = Profile.objects.filter(telegram_link_token=token).select_related('user').first()
    if profile is None:
        _reply(chat_id, _in_language(None, lambda: _(
            'Ссылка недействительна или устарела. Создайте новую в личном кабинете.'
        )))
        return
    # a chat can belong to one account only
    Profile.objects.filter(telegram_chat_id=chat_id).exclude(pk=profile.pk).update(
        telegram_chat_id=None
    )
    profile.telegram_chat_id = chat_id
    profile.telegram_link_token = ''
    profile.save(update_fields=['telegram_chat_id', 'telegram_link_token', 'updated_at'])
    _reply(chat_id, _in_language(profile.notification_language, lambda: _(
        '✅ Telegram подключён к аккаунту %(username)s. '
        'Отключить уведомления можно командой /stop.'
    ) % {'username': profile.user.username}))


def _unlink(chat_id):
    profile = Profile.objects.filter(telegram_chat_id=chat_id).first()
    if profile is None:
        return
    language = profile.notification_language
    profile.telegram_chat_id = None
    profile.save(update_fields=['telegram_chat_id', 'updated_at'])
    _reply(chat_id, _in_language(language, lambda: _(
        'Уведомления в Telegram отключены.'
    )))
