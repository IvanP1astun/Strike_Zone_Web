"""Attendance marks and player statistics."""
from datetime import timedelta
from itertools import count

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from main.models import AirsoftGame, GameRegistration, Profile
from main.stats import player_stats

pytestmark = pytest.mark.django_db

User = get_user_model()
_numbers = count(1)


def make_user(**extra):
    number = next(_numbers)
    return User.objects.create_user(
        username='player%d' % number, password='pass12345',
        email='p%d@example.com' % number, **extra,
    )


def make_game(days=-1, **extra):
    number = next(_numbers)
    extra.setdefault('max_players', 20)
    return AirsoftGame.objects.create(
        name='Игра %d' % number, date=timezone.localdate() + timedelta(days=days), **extra
    )


def register(game, user=None, status='yes', **extra):
    number = next(_numbers)
    return GameRegistration.objects.create(
        game=game, user=user, first_name='Имя%d' % number, last_name='Фамилия%d' % number,
        phone_number='+7900%07d' % number, participation_status=status, **extra,
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_superuser('boss', 'boss@example.com', 'pass12345')


# ----------------------------------------------------------------- statistics

def test_stats_for_a_new_player():
    stats = player_stats(make_user())
    assert stats['played'] == 0
    assert stats['missed'] == 0
    assert stats['attendance_rate'] is None
    assert stats['badges'] == []
    assert stats['next_badge']['left'] == 1
    assert stats['first_game'] is None


def test_stats_counts_marks_and_rate():
    user = make_user()
    for mark in (True, True, True, False):
        register(make_game(days=-5), user, attended=mark)
    register(make_game(days=-3), user)  # not marked: ignored in the rate
    stats = player_stats(user)
    assert stats['played'] == 3
    assert stats['missed'] == 1
    assert stats['attendance_rate'] == 75


def test_stats_upcoming_counts_only_confirmed_future_games():
    user = make_user()
    register(make_game(days=3), user)
    register(make_game(days=0), user)  # today still counts
    register(make_game(days=4), user, status='unknown')
    register(make_game(days=-2), user)
    waiting_game = make_game(days=5, max_players=1)
    register(waiting_game, make_user())
    register(waiting_game, user)  # lands on the waiting list
    assert player_stats(user)['upcoming'] == 2


def test_stats_first_and_last_game():
    user = make_user()
    register(make_game(days=-20), user, attended=True)
    register(make_game(days=-2), user, attended=True)
    register(make_game(days=-10), user, attended=False)
    stats = player_stats(user)
    assert stats['first_game'] == timezone.localdate() - timedelta(days=20)
    assert stats['last_game'] == timezone.localdate() - timedelta(days=2)


@pytest.mark.parametrize(
    'played, titles, left',
    [(0, [], 1), (1, ['Новичок'], 4), (5, ['Новичок', 'Боец'], 5),
     (10, ['Новичок', 'Боец', 'Ветеран'], 15), (25, ['Новичок', 'Боец', 'Ветеран', 'Легенда'], None)],
)
def test_badges(played, titles, left):
    user = make_user()
    for _ in range(played):
        register(make_game(days=-1), user, attended=True)
    stats = player_stats(user)
    assert [str(b['title']) for b in stats['badges']] == titles
    assert (stats['next_badge'] or {}).get('left') == left


def test_other_players_marks_do_not_leak():
    me, other = make_user(), make_user()
    register(make_game(), other, attended=True)
    assert player_stats(me)['played'] == 0


def test_profile_page_shows_the_statistics(client):
    user = make_user()
    Profile.objects.create(user=user)
    register(make_game(days=-3), user, attended=True)
    register(make_game(days=-2), user, attended=False)
    client.force_login(user)
    response = client.get(reverse('profile'))
    assert response.context['stats']['played'] == 1
    page = response.content.decode()
    assert 'player-stats' in page
    assert '50%' in page
    assert 'Новичок' in page


# ------------------------------------------------------------ attendance page

def test_attendance_requires_permission(client):
    game = make_game()
    url = reverse('game_attendance', args=[game.id])
    assert client.get(url).status_code == 302  # login page
    client.force_login(make_user())
    assert client.get(url).status_code == 403


def test_organizer_sees_only_confirmed_participants(client, organizer):
    game = make_game(max_players=1)
    confirmed = register(game, make_user())
    register(game, make_user())  # waiting list
    register(game, make_user(), status='no')
    client.force_login(organizer)
    response = client.get(reverse('game_attendance', args=[game.id]))
    assert response.status_code == 200
    assert response.context['registrations'] == [confirmed]
    assert response.context['total'] == 1


def test_marks_are_saved(client, organizer):
    game = make_game()
    came, absent, unmarked = (register(game, make_user()) for _ in range(3))
    client.force_login(organizer)
    response = client.post(reverse('game_attendance', args=[game.id]), {
        'attended_%d' % came.id: '1',
        'attended_%d' % absent.id: '0',
        'attended_%d' % unmarked.id: '',
    })
    assert response.status_code == 302
    for registration in (came, absent, unmarked):
        registration.refresh_from_db()
    assert came.attended is True
    assert absent.attended is False
    assert unmarked.attended is None


def test_a_mark_can_be_changed_and_cleared(client, organizer):
    game = make_game()
    registration = register(game, make_user(), attended=True)
    client.force_login(organizer)
    url = reverse('game_attendance', args=[game.id])
    client.post(url, {'attended_%d' % registration.id: '0'})
    registration.refresh_from_db()
    assert registration.attended is False
    client.post(url, {'attended_%d' % registration.id: ''})
    registration.refresh_from_db()
    assert registration.attended is None


def test_invalid_or_missing_values_keep_the_mark(client, organizer):
    game = make_game()
    registration = register(game, make_user(), attended=True)
    client.force_login(organizer)
    url = reverse('game_attendance', args=[game.id])
    client.post(url, {'attended_%d' % registration.id: 'banana'})
    client.post(url, {})
    registration.refresh_from_db()
    assert registration.attended is True


def test_marks_do_not_touch_other_games_or_the_waiting_list(client, organizer):
    game, other = make_game(), make_game()
    foreign = register(other, make_user())
    client.force_login(organizer)
    client.post(reverse('game_attendance', args=[game.id]), {'attended_%d' % foreign.id: '1'})
    foreign.refresh_from_db()
    assert foreign.attended is None


def test_marking_does_not_change_places(client, organizer):
    game = make_game(max_players=2)
    first, second = register(game, make_user()), register(game, make_user())
    client.force_login(organizer)
    client.post(reverse('game_attendance', args=[game.id]), {
        'attended_%d' % first.id: '0', 'attended_%d' % second.id: '1',
    })
    game.refresh_from_db()
    assert game.registered_players == 2


def test_cannot_mark_before_the_game_day(client, organizer):
    game = make_game(days=2)
    registration = register(game, make_user())
    client.force_login(organizer)
    url = reverse('game_attendance', args=[game.id])
    assert client.get(url).status_code == 302
    client.post(url, {'attended_%d' % registration.id: '1'})
    registration.refresh_from_db()
    assert registration.attended is None


def test_marking_is_possible_on_the_game_day(client, organizer):
    game = make_game(days=0)
    assert client.get(reverse('game_attendance', args=[game.id])).status_code == 302
    client.force_login(organizer)
    assert client.get(reverse('game_attendance', args=[game.id])).status_code == 200


def test_game_page_button_only_for_organizers_after_the_game_starts(client, organizer):
    past, future = make_game(days=-1), make_game(days=3)
    url_past = reverse('game_attendance', args=[past.id])

    page = client.get(reverse('game_detail', args=[past.id])).content.decode()
    assert url_past not in page  # anonymous

    client.force_login(make_user())
    page = client.get(reverse('game_detail', args=[past.id])).content.decode()
    assert url_past not in page  # ordinary player

    client.force_login(organizer)
    assert url_past in client.get(reverse('game_detail', args=[past.id])).content.decode()
    page = client.get(reverse('game_detail', args=[future.id])).content.decode()
    assert reverse('game_attendance', args=[future.id]) not in page


def test_attendance_page_is_translated(client, organizer):
    game = make_game()
    register(game, make_user())
    client.force_login(organizer)
    page = client.get(reverse('game_attendance', args=[game.id]), headers={'accept-language': 'ja'})
    assert 'ゲームの出欠' in page.content.decode()
