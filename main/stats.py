"""Player statistics for the profile page."""
from django.db.models import Max, Min
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import GameRegistration

# (games played, icon, title)
BADGES = [
    (1, '🥉', _('Новичок')),
    (5, '🥈', _('Боец')),
    (10, '🥇', _('Ветеран')),
    (25, '🏆', _('Легенда')),
]


def player_stats(user, today=None):
    """Numbers shown on the profile page.

    Attendance is marked by the organizer after a game, so the percentage is
    calculated only from games that were marked.
    """
    today = today or timezone.localdate()
    registrations = GameRegistration.objects.filter(user=user)

    played = registrations.filter(attended=True).count()
    missed = registrations.filter(attended=False).count()
    marked = played + missed
    upcoming = registrations.filter(
        participation_status='yes', is_waitlisted=False, game__date__gte=today
    ).count()
    dates = registrations.filter(attended=True).aggregate(
        first=Min('game__date'), last=Max('game__date')
    )

    earned = [
        {'icon': icon, 'title': title, 'games': games}
        for games, icon, title in BADGES if played >= games
    ]
    upcoming_badge = next(
        ({'icon': icon, 'title': title, 'left': games - played}
         for games, icon, title in BADGES if played < games),
        None,
    )
    return {
        'played': played,
        'missed': missed,
        'attendance_rate': round(played * 100 / marked) if marked else None,
        'upcoming': upcoming,
        'first_game': dates['first'],
        'last_game': dates['last'],
        'badges': earned,
        'next_badge': upcoming_badge,
    }
