import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_telegram_message(text):
    """Отправляет сообщение в Telegram"""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    
    if not token or not chat_id:
        logger.error("Telegram token or chat_id is missing!")
        return
    
    url = f"https: //api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }
    
    try:
        requests.post(url, data=payload, timeout=5)
    except requests.RequestException:
        pass
