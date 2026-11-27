"""Notifications to players by email and Telegram.

Every public notify_* function is safe to call from signals and views: it never
raises, respects the player's preferences and writes the text in the player's
chosen notification language. Only registrations linked to a site account can be
notified (an anonymous registration has neither an email nor a Telegram chat).
"""
import html
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from .notifications import send_telegram_to

logger = logging.getLogger(__name__)

SUBJECT_PREFIX = 'StrikeZone: '


def _profile(user):
    return getattr(user, 'profile', None)


def language_for(user):
    profile = _profile(user)
    code = getattr(profile, 'notification_language', '') or settings.LANGUAGE_CODE
    return code if code in dict(settings.LANGUAGES) else settings.LANGUAGE_CODE


def game_url(game):
    base = getattr(settings, 'SITE_URL', '')
    return base + reverse('game_detail', args=[game.id]) if base else ''


def _game_lines(game):
    lines = [_('Дата: %(date)s') % {'date': date_format(game.date, 'DATE_FORMAT')}]
    if game.location:
        lines.append(_('Место: %(location)s') % {'location': game.location})
    return lines


def deliver(user, build):
    """Send one notification to a user through the channels they enabled.

    build() runs under the user's language and returns (subject, lines, url).
    Returns the list of channels used ('email', 'telegram').
    """
    used = []
    try:
        profile = _profile(user)
        want_email = profile.notify_email if profile else True
        want_telegram = profile.notify_telegram if profile else True
        chat_id = getattr(profile, 'telegram_chat_id', None)
        send_by_email = bool(want_email and user.email)
        send_by_telegram = bool(want_telegram and chat_id)
        if not (send_by_email or send_by_telegram):
            return used

        with translation.override(language_for(user)):
            subject, lines, url = build()
        body = '\n'.join(lines + ([url] if url else []))

        if send_by_email:
            try:
                send_mail(
                    SUBJECT_PREFIX + subject, body, settings.DEFAULT_FROM_EMAIL, [user.email]
                )
                used.append('email')
            except Exception:
                logger.exception('Email to %s failed', user.pk)
        if send_by_telegram:
            text = '<b>%s</b>\n%s' % (
                html.escape(subject),
                html.escape('\n'.join(lines)),
            )
            if url:
                text += '\n' + html.escape(url)
            if send_telegram_to(chat_id, text):
                used.append('telegram')
    except Exception:
        logger.exception('Notification to user %s failed', getattr(user, 'pk', None))
    return used


# --------------------------------------------------------------- recipients

def recipients_of(game):
    """Accounts that have a registration for the game (coming, maybe, waiting)."""
    registrations = game.registrations.filter(user__isnull=False).exclude(
        participation_status='no'
    ).select_related('user', 'user__profile')
    seen, users = set(), []
    for registration in registrations:
        if registration.user_id not in seen:
            seen.add(registration.user_id)
            users.append(registration.user)
    return users


# ------------------------------------------------------------------- events

def notify_registration(registration):
    """The player registered (or changed the answer): confirm the place or the queue."""
    user = registration.user
    if user is None:
        return []
    game = registration.game

    if registration.is_waitlisted:
        def build():
            return (
                _('Вы в листе ожидания: %(game)s') % {'game': game.name},
                [
                    _('Свободных мест нет, ваша позиция в очереди — %(position)s.')
                    % {'position': registration.waitlist_position},
                    _('Если место освободится, вы получите его автоматически.'),
                ] + _game_lines(game),
                game_url(game),
            )
    elif registration.participation_status == 'yes':
        def build():
            return (
                _('Вы зарегистрированы: %(game)s') % {'game': game.name},
                [_('Ваше место на игре закреплено.')] + _game_lines(game),
                game_url(game),
            )
    else:
        return []
    return deliver(user, build)


def notify_promoted(registration):
    """A place was freed and the player moved up from the waiting list."""
    user = registration.user
    if user is None:
        return []
    game = registration.game

    def build():
        return (
            _('Для вас освободилось место: %(game)s') % {'game': game.name},
            [_('Вы переведены из листа ожидания в список участников.')]
            + _game_lines(game),
            game_url(game),
        )
    return deliver(user, build)


def notify_game_changed(game, changes):
    """The date and/or place of a game changed: tell everybody who is registered."""
    for user in recipients_of(game):
        def build():
            lines = []
            if 'date' in changes:
                lines.append(
                    _('Новая дата: %(new)s (раньше: %(old)s)') % {
                        'new': date_format(game.date, 'DATE_FORMAT'),
                        'old': date_format(changes['date'], 'DATE_FORMAT'),
                    }
                )
            if 'location' in changes:
                lines.append(
                    _('Новое место: %(new)s (раньше: %(old)s)') % {
                        'new': game.location or '—',
                        'old': changes['location'] or '—',
                    }
                )
            return (
                _('Изменения в игре: %(game)s') % {'game': game.name},
                lines,
                game_url(game),
            )
        deliver(user, build)


def notify_game_cancelled(name, game_date, users):
    """The game was deleted."""
    for user in users:
        def build():
            return (
                _('Игра отменена: %(game)s') % {'game': name},
                [
                    _('Игра, назначенная на %(date)s, отменена.')
                    % {'date': date_format(game_date, 'DATE_FORMAT')}
                ],
                '',
            )
        deliver(user, build)


def notify_reminder(user, game):
    def build():
        return (
            _('Напоминание: скоро игра «%(game)s»') % {'game': game.name},
            [_('Не забудьте про игру!')] + _game_lines(game),
            game_url(game),
        )
    return deliver(user, build)


def send_reminders(days_ahead=1, today=None):
    """Remind confirmed players about games that start in `days_ahead` days.

    Each game is processed once (reminder_sent_at). Returns the number of
    players that were reminded. Run it daily, see the README.
    """
    from .models import AirsoftGame

    target = (today or timezone.localdate()) + timedelta(days=days_ahead)
    games = AirsoftGame.objects.filter(
        is_active=True, date=target, reminder_sent_at__isnull=True
    )
    reminded = 0
    for game in games:
        registrations = game.registrations.filter(
            participation_status='yes', is_waitlisted=False, user__isnull=False
        ).select_related('user', 'user__profile')
        for registration in registrations:
            notify_reminder(registration.user, game)
            reminded += 1
        AirsoftGame.objects.filter(pk=game.pk).update(reminder_sent_at=timezone.now())
    return reminded
