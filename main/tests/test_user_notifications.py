"""Email and Telegram notifications to players."""
import json
from datetime import timedelta
from itertools import count
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from main import user_notifications
from main.models import AirsoftGame, GameRegistration, Profile

pytestmark = pytest.mark.django_db

User = get_user_model()
_numbers = count(1)


def make_user(email=True, language='ru', chat_id=None, **profile_fields):
    number = next(_numbers)
    user = User.objects.create_user(
        username='player%d' % number,
        password='pass12345',
        email='player%d@example.com' % number if email else '',
    )
    Profile.objects.create(
        user=user, notification_language=language, telegram_chat_id=chat_id, **profile_fields
    )
    return user


def make_game(days=10, **extra):
    extra.setdefault('max_players', 20)
    extra.setdefault('name', 'Операция Шторм')  # game names are unique
    return AirsoftGame.objects.create(
        date=timezone.localdate() + timedelta(days=days), location='Лес', **extra
    )


def register(game, user, status='yes'):
    return GameRegistration.objects.create(
        game=game, user=user, first_name='Имя', last_name='Фамилия',
        phone_number='+7900%07d' % next(_numbers), participation_status=status,
    )


@pytest.fixture
def telegram():
    with mock.patch('main.user_notifications.send_telegram_to', return_value=True) as send:
        yield send


# ------------------------------------------------------------------ channels

def test_email_is_sent_with_prefix_and_in_users_language():
    user = make_user(language='en')
    game = make_game()
    registration = register(game, user)

    used = user_notifications.notify_registration(registration)

    assert used == ['email']
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [user.email]
    assert message.subject == 'StrikeZone: You are registered: Операция Шторм'
    assert 'Your place in the game is secured.' in message.body


def test_japanese_notification():
    user = make_user(language='ja')
    registration = register(make_game(), user)
    user_notifications.notify_registration(registration)
    assert 'ゲームへの参加枠が確保されました' in mail.outbox[0].body


def test_unknown_language_falls_back_to_russian():
    user = make_user(language='xx')
    registration = register(make_game(), user)
    user_notifications.notify_registration(registration)
    assert 'Вы зарегистрированы' in mail.outbox[0].subject


def test_telegram_message_is_sent_and_escaped(telegram):
    user = make_user(email=False, chat_id=777)
    game = AirsoftGame.objects.create(
        name='A <b>&</b> B', date=timezone.localdate() + timedelta(days=3), max_players=5
    )
    used = user_notifications.notify_registration(register(game, user))

    assert used == ['telegram']
    chat_id, text = telegram.call_args.args
    assert chat_id == 777
    assert '&lt;b&gt;&amp;&lt;/b&gt;' in text
    assert '<b>Вы зарегистрированы' in text
    assert mail.outbox == []


def test_both_channels(telegram):
    user = make_user(chat_id=555)
    used = user_notifications.notify_registration(register(make_game(), user))
    assert used == ['email', 'telegram']


def test_preferences_are_respected(telegram):
    user = make_user(chat_id=555, notify_email=False, notify_telegram=False)
    assert user_notifications.notify_registration(register(make_game(), user)) == []
    assert mail.outbox == []
    telegram.assert_not_called()


def test_user_without_contacts_gets_nothing(telegram):
    user = make_user(email=False)
    assert user_notifications.notify_registration(register(make_game(), user)) == []
    telegram.assert_not_called()


def test_user_without_profile_gets_email_by_default():
    user = User.objects.create_user('noprofile', 'np@example.com', 'pass12345')
    registration = register(make_game(), user)
    assert user_notifications.notify_registration(registration) == ['email']


def test_anonymous_registration_is_skipped():
    game = make_game()
    registration = GameRegistration.objects.create(
        game=game, first_name='А', last_name='Б', phone_number='+79000000000',
        participation_status='yes',
    )
    assert user_notifications.notify_registration(registration) == []


def test_failing_email_backend_does_not_break_the_caller(settings):
    user = make_user()
    registration = register(make_game(), user)
    with mock.patch('main.user_notifications.send_mail', side_effect=OSError('smtp down')):
        assert user_notifications.notify_registration(registration) == []


def test_no_notification_for_not_coming_status():
    user = make_user()
    registration = register(make_game(), user, status='no')
    assert user_notifications.notify_registration(registration) == []


# -------------------------------------------------------------------- events

def test_registering_through_the_page_sends_confirmation(client, django_capture_on_commit_callbacks):
    user = make_user()
    game = make_game()
    client.force_login(user)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse('game_detail', args=[game.id]),
            data={
                'first_name': 'Пётр', 'last_name': 'Иванов', 'phone_number': '+79001112233',
                'participation_status': 'yes', 'has_equipment': 'yes',
            },
        )
    assert GameRegistration.objects.filter(game=game, user=user).exists()
    assert len(mail.outbox) == 1
    assert 'Вы зарегистрированы' in mail.outbox[0].subject


def test_waiting_player_is_told_when_a_place_frees_up(django_capture_on_commit_callbacks):
    first, second = make_user(), make_user(language='en')
    game = make_game(max_players=1)
    taken = register(game, first)
    waiting = register(game, second)
    waiting.refresh_from_db()
    assert waiting.is_waitlisted

    with django_capture_on_commit_callbacks(execute=True):
        taken.delete()

    assert [m.to for m in mail.outbox] == [[second.email]]
    assert 'A place has become free for you' in mail.outbox[0].subject


def test_raising_the_limit_notifies_promoted_players(django_capture_on_commit_callbacks):
    first, second = make_user(), make_user()
    game = make_game(max_players=1)
    register(game, first)
    register(game, second)
    mail.outbox.clear()

    game.max_players = 2
    with django_capture_on_commit_callbacks(execute=True):
        game.save()

    assert [m.to for m in mail.outbox] == [[second.email]]


def test_changing_the_date_notifies_registered_players(django_capture_on_commit_callbacks):
    coming, maybe, not_coming = make_user(), make_user(), make_user()
    game = make_game()
    register(game, coming)
    register(game, maybe, status='unknown')
    register(game, not_coming, status='no')
    old_date = game.date

    game.date = old_date + timedelta(days=2)
    with django_capture_on_commit_callbacks(execute=True):
        game.save()

    recipients = sorted(m.to[0] for m in mail.outbox)
    assert recipients == sorted([coming.email, maybe.email])
    assert 'Изменения в игре' in mail.outbox[0].subject
    assert 'Новая дата' in mail.outbox[0].body


def test_changing_the_location_notifies(django_capture_on_commit_callbacks):
    user = make_user()
    game = make_game()
    register(game, user)

    game.location = 'Новый полигон'
    with django_capture_on_commit_callbacks(execute=True):
        game.save()

    assert 'Новое место: Новый полигон (раньше: Лес)' in mail.outbox[0].body


def test_saving_without_changes_sends_nothing(django_capture_on_commit_callbacks):
    user = make_user()
    game = make_game()
    register(game, user)

    game.description = 'Только описание'
    with django_capture_on_commit_callbacks(execute=True):
        game.save()

    assert mail.outbox == []


def test_moving_the_game_resets_the_reminder():
    game = make_game(days=1)
    AirsoftGame.objects.filter(pk=game.pk).update(reminder_sent_at=timezone.now())
    game.refresh_from_db()
    assert game.reminder_sent_at is not None

    game.date = game.date + timedelta(days=1)
    game.save()

    game.refresh_from_db()
    assert game.reminder_sent_at is None


def test_deleting_the_game_notifies_participants(django_capture_on_commit_callbacks):
    coming, not_coming = make_user(), make_user()
    game = make_game()
    register(game, coming)
    register(game, not_coming, status='no')

    with django_capture_on_commit_callbacks(execute=True):
        game.delete()

    assert [m.to for m in mail.outbox] == [[coming.email]]
    assert 'Игра отменена: Операция Шторм' in mail.outbox[0].subject


def test_deleting_a_full_game_does_not_send_place_freed_messages(django_capture_on_commit_callbacks):
    first, second = make_user(), make_user()
    game = make_game(max_players=1)
    register(game, first)
    register(game, second)

    with django_capture_on_commit_callbacks(execute=True):
        game.delete()

    assert all('освободилось' not in m.subject for m in mail.outbox)


# ----------------------------------------------------------------- reminders

def test_reminders_go_to_confirmed_players_once():
    confirmed, waiting, no = make_user(), make_user(), make_user()
    game = make_game(days=1, max_players=1)
    register(game, confirmed)
    register(game, waiting)  # goes to the waiting list
    register(game, no, status='no')
    other_day = make_game(days=5, name='Другая игра')
    register(other_day, make_user())
    mail.outbox.clear()

    assert user_notifications.send_reminders(today=timezone.localdate()) == 1
    assert [m.to for m in mail.outbox] == [[confirmed.email]]
    assert 'Напоминание' in mail.outbox[0].subject

    assert user_notifications.send_reminders(today=timezone.localdate()) == 0
    assert len(mail.outbox) == 1


def test_reminder_command():
    user = make_user()
    register(make_game(days=1), user)
    mail.outbox.clear()
    call_command('send_game_reminders')
    assert len(mail.outbox) == 1
    call_command('send_game_reminders')
    assert len(mail.outbox) == 1


# ------------------------------------------------------- profile preferences

def test_notification_settings_are_saved(client):
    user = make_user()
    client.force_login(user)
    response = client.post(reverse('notification_settings'), {
        'notification_language': 'ja', 'notify_telegram': 'on',
    })
    assert response.status_code == 302
    user.profile.refresh_from_db()
    assert user.profile.notification_language == 'ja'
    assert user.profile.notify_email is False
    assert user.profile.notify_telegram is True


def test_notification_settings_reject_unknown_language(client):
    user = make_user()
    client.force_login(user)
    client.post(reverse('notification_settings'), {'notification_language': 'xx'})
    user.profile.refresh_from_db()
    assert user.profile.notification_language == 'ru'


def test_notification_views_require_login_and_post(client):
    for name in ('notification_settings', 'telegram_connect', 'telegram_disconnect'):
        assert client.post(reverse(name)).status_code == 302  # to the login page
    user = make_user()
    client.force_login(user)
    for name in ('notification_settings', 'telegram_connect', 'telegram_disconnect'):
        assert client.get(reverse(name)).status_code == 405


def test_profile_page_shows_notification_settings(client, settings):
    settings.TELEGRAM_BOT_USERNAME = 'strikezone_bot'
    user = make_user()
    client.force_login(user)
    page = client.get(reverse('profile')).content.decode()
    assert reverse('notification_settings') in page
    assert reverse('telegram_connect') in page


def test_telegram_connect_creates_a_one_time_link(client, settings):
    settings.TELEGRAM_BOT_USERNAME = 'strikezone_bot'
    user = make_user()
    client.force_login(user)
    client.post(reverse('telegram_connect'))
    user.profile.refresh_from_db()
    token = user.profile.telegram_link_token
    assert len(token) >= 16
    page = client.get(reverse('profile')).content.decode()
    assert 'https://t.me/strikezone_bot?start=%s' % token in page


def test_telegram_connect_needs_a_configured_bot(client, settings):
    settings.TELEGRAM_BOT_USERNAME = ''
    user = make_user()
    client.force_login(user)
    client.post(reverse('telegram_connect'))
    user.profile.refresh_from_db()
    assert user.profile.telegram_link_token == ''


def test_telegram_disconnect(client):
    user = make_user(chat_id=999, telegram_link_token='abc')
    client.force_login(user)
    client.post(reverse('telegram_disconnect'))
    user.profile.refresh_from_db()
    assert user.profile.telegram_chat_id is None
    assert user.profile.telegram_link_token == ''


# ------------------------------------------------------------ bot / webhook

SECRET = 'webhook-secret'


def post_update(client, text, chat_id=4242, chat_type='private', secret=SECRET):
    update = {'message': {'text': text, 'chat': {'id': chat_id, 'type': chat_type}}}
    headers = {'X-Telegram-Bot-Api-Secret-Token': secret} if secret is not None else {}
    return client.post(
        reverse('telegram_webhook'), data=json.dumps(update),
        content_type='application/json', headers=headers,
    )


@pytest.fixture
def bot(settings):
    settings.TELEGRAM_WEBHOOK_SECRET = SECRET
    settings.TELEGRAM_BOT_TOKEN = 'token'
    with mock.patch('main.telegram_bot.send_telegram_to', return_value=True) as send:
        yield send


def test_webhook_is_hidden_without_a_secret(client, settings):
    settings.TELEGRAM_WEBHOOK_SECRET = ''
    assert post_update(client, '/start', secret='x').status_code == 404


def test_webhook_rejects_a_wrong_or_missing_secret(client, bot):
    assert post_update(client, '/start', secret='wrong').status_code == 403
    assert post_update(client, '/start', secret=None).status_code == 403
    bot.assert_not_called()


def test_webhook_accepts_only_post(client, bot):
    assert client.get(reverse('telegram_webhook')).status_code == 405


def test_webhook_rejects_broken_json(client, bot):
    response = client.post(
        reverse('telegram_webhook'), data='not json', content_type='application/json',
        headers={'X-Telegram-Bot-Api-Secret-Token': SECRET},
    )
    assert response.status_code == 400


def test_start_with_a_valid_code_links_the_chat(client, bot):
    user = make_user(language='en', telegram_link_token='code123')
    response = post_update(client, '/start code123', chat_id=31337)
    assert response.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.telegram_chat_id == 31337
    assert user.profile.telegram_link_token == ''
    chat_id, text = bot.call_args.args
    assert chat_id == 31337
    assert user.username in text
    assert 'connected' in text


def test_code_works_only_once(client, bot):
    make_user(telegram_link_token='code123')
    post_update(client, '/start code123', chat_id=1)
    bot.reset_mock()
    post_update(client, '/start code123', chat_id=2)
    assert 'недействительна' in bot.call_args.args[1]


def test_unknown_code_is_refused(client, bot):
    user = make_user()
    post_update(client, '/start nonsense')
    user.profile.refresh_from_db()
    assert user.profile.telegram_chat_id is None
    assert 'недействительна' in bot.call_args.args[1]


def test_empty_token_never_matches(client, bot):
    user = make_user()  # token is '' by default
    post_update(client, '/start ')
    user.profile.refresh_from_db()
    assert user.profile.telegram_chat_id is None


def test_a_chat_belongs_to_one_account_only(client, bot):
    old = make_user(chat_id=555)
    new = make_user(telegram_link_token='fresh')
    post_update(client, '/start fresh', chat_id=555)
    old.profile.refresh_from_db()
    new.profile.refresh_from_db()
    assert old.profile.telegram_chat_id is None
    assert new.profile.telegram_chat_id == 555


def test_start_without_a_code_explains_what_to_do(client, bot):
    post_update(client, '/start')
    assert 'Подключить Telegram' in bot.call_args.args[1]


def test_stop_disconnects(client, bot):
    user = make_user(chat_id=808)
    post_update(client, '/stop', chat_id=808)
    user.profile.refresh_from_db()
    assert user.profile.telegram_chat_id is None
    bot.assert_called_once()


def test_group_chats_and_plain_text_are_ignored(client, bot):
    make_user(telegram_link_token='code123')
    post_update(client, '/start code123', chat_type='group')
    post_update(client, 'hello')
    bot.assert_not_called()


def test_webhook_answers_200_even_if_processing_fails(client, bot):
    with mock.patch('main.views.telegram_bot.handle_update', side_effect=RuntimeError('boom')):
        assert post_update(client, '/start x').status_code == 200


# ------------------------------------------------------- set_telegram_webhook

def test_set_webhook_command(settings):
    settings.TELEGRAM_BOT_TOKEN = 'token'
    settings.TELEGRAM_WEBHOOK_SECRET = SECRET
    settings.SITE_URL = 'https://club.example.com'
    with mock.patch('main.management.commands.set_telegram_webhook.requests.post') as post:
        post.return_value.status_code = 200
        post.return_value.json.return_value = {'description': 'Webhook was set'}
        call_command('set_telegram_webhook')
    url = post.call_args.args[0]
    payload = post.call_args.kwargs['data']
    assert url == 'https://api.telegram.org/bottoken/setWebhook'
    assert payload['url'] == 'https://club.example.com/telegram/webhook/'
    assert payload['secret_token'] == SECRET


def test_set_webhook_command_needs_https_and_secret(settings):
    settings.TELEGRAM_BOT_TOKEN = 'token'
    settings.TELEGRAM_WEBHOOK_SECRET = ''
    settings.SITE_URL = 'https://club.example.com'
    with pytest.raises(CommandError):
        call_command('set_telegram_webhook')
    settings.TELEGRAM_WEBHOOK_SECRET = SECRET
    settings.SITE_URL = 'http://club.example.com'
    with pytest.raises(CommandError):
        call_command('set_telegram_webhook')
