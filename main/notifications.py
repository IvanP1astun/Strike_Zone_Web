import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Not an f-string on purpose: pycodestyle 2.10 reports a false E231 for ':'
# inside f-strings on Python 3.12.
TELEGRAM_API_URL = 'https://api.telegram.org/bot{token}/sendMessage'


def _post_telegram(token, chat_id, text):
    """Send one message; never raises. Returns True on HTTP 200."""
    url = TELEGRAM_API_URL.format(token=token)
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }

    try:
        response = requests.post(url, data=payload, timeout=5)
        logger.info('Telegram: %s', response.status_code)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error('Ошибка отправки в Telegram: %s', e)
        return False


def send_telegram_message(text):
    """Отправляет сообщение администратору в Telegram (безопасно, не ломает приложение)"""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)

    if not token or not chat_id:
        logger.warning('TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы — уведомление пропущено')
        return

    _post_telegram(token, chat_id, text)


def send_telegram_to(chat_id, text):
    """Отправляет сообщение конкретному пользователю (по его chat_id)."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token or not chat_id:
        logger.warning('Telegram: нет токена бота или chat_id — сообщение пропущено')
        return False
    return _post_telegram(token, chat_id, text)
