import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(text):
    """Отправляет сообщение в Telegram (безопасно, не ломает приложение)"""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)

    if not token or not chat_id:
        logger.warning('TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы — уведомление пропущено')
        return

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }

    try:
        response = requests.post(url, data=payload, timeout=5)
        logger.info('Telegram: %s', response.status_code)
    except requests.RequestException as e: 
        logger.error('Ошибка отправки в Telegram: %s', e)
