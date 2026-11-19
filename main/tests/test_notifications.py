from unittest import mock

from main.notifications import send_telegram_message


def test_send_telegram_message_uses_valid_url(settings):
    settings.TELEGRAM_BOT_TOKEN = 'token'
    settings.TELEGRAM_CHAT_ID = '123'

    with mock.patch('main.notifications.requests.post') as post:
        send_telegram_message('hello')

    url = post.call_args.args[0]
    assert url == 'https://api.telegram.org/bottoken/sendMessage'
    assert ' ' not in url


def test_send_telegram_message_skipped_without_credentials(settings):
    settings.TELEGRAM_BOT_TOKEN = ''
    settings.TELEGRAM_CHAT_ID = ''

    with mock.patch('main.notifications.requests.post') as post:
        send_telegram_message('hello')

    post.assert_not_called()
