import requests
from django.conf import settings


def send_telegram_message(text):
    """Отправляет сообщение в Telegram"""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    
    if not token or not chat_id:
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }
    
    try:
        requests.post(url, data=payload, timeout=5)
    except requests.RequestException:
        pass
