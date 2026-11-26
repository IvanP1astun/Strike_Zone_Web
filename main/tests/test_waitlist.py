"""Game capacity and the waiting list."""
from datetime import date, timedelta
from itertools import count

import pytest
from django.urls import reverse

from main.models import AirsoftGame, GameRegistration

pytestmark = pytest.mark.django_db

_phones = count(1)


@pytest.fixture
def small_game(db):
    """A game with only two places."""
    return AirsoftGame.objects.create(
        name="Маленькая игра", date=date.today() + timedelta(days=5), max_players=2
    )


def register(game, status="yes", **extra):
    number = next(_phones)
    return GameRegistration.objects.create(
        game=game,
        first_name="Игрок%d" % number,
        last_name="Тестов",
        phone_number="+7900000%04d" % number,
        participation_status=status,
        **extra,
    )


def refreshed(game):
    game.refresh_from_db()
    return game


def test_confirmed_registrations_take_places(small_game):
    register(small_game)
    register(small_game, status="unknown")  # holds no place
    register(small_game, status="no")  # holds no place
    game = refreshed(small_game)
    assert game.registered_players == 1
    assert game.places_left == 1
    assert not game.is_full


def test_third_player_goes_to_waitlist(small_game):
    first, second, third = (register(small_game) for _ in range(3))
    assert not first.is_waitlisted and not second.is_waitlisted
    third.refresh_from_db()
    assert third.is_waitlisted
    assert third.waitlisted_at is not None
    assert third.waitlist_position == 1
    game = refreshed(small_game)
    assert game.registered_players == 2
    assert game.is_full
    assert game.places_left == 0


def test_waitlist_keeps_order(small_game):
    register(small_game)
    register(small_game)
    third, fourth = register(small_game), register(small_game)
    third.refresh_from_db()
    fourth.refresh_from_db()
    assert third.waitlist_position == 1
    assert fourth.waitlist_position == 2


def test_cancelling_promotes_the_first_in_line(small_game):
    first = register(small_game)
    register(small_game)
    third, fourth = register(small_game), register(small_game)

    first.delete()

    third.refresh_from_db()
    fourth.refresh_from_db()
    assert not third.is_waitlisted
    assert third.waitlisted_at is None
    assert fourth.is_waitlisted
    assert fourth.waitlist_position == 1
    assert refreshed(small_game).registered_players == 2


def test_changing_status_to_no_frees_a_place(small_game):
    first = register(small_game)
    register(small_game)
    third = register(small_game)

    first.participation_status = "no"
    first.save()

    third.refresh_from_db()
    assert not third.is_waitlisted
    assert refreshed(small_game).registered_players == 2


def test_waiting_player_who_changes_mind_leaves_the_queue(small_game):
    register(small_game)
    register(small_game)
    third = register(small_game)
    third.refresh_from_db()
    assert third.is_waitlisted

    third.participation_status = "no"
    third.save()

    third.refresh_from_db()
    assert not third.is_waitlisted
    assert third.waitlisted_at is None
    assert refreshed(small_game).registered_players == 2


def test_unknown_becoming_yes_on_a_full_game_waits(small_game):
    register(small_game)
    register(small_game)
    maybe = register(small_game, status="unknown")
    assert not maybe.is_waitlisted

    maybe.participation_status = "yes"
    maybe.save()

    maybe.refresh_from_db()
    assert maybe.is_waitlisted


def test_raising_the_limit_promotes_waiting_players(small_game):
    register(small_game)
    register(small_game)
    third = register(small_game)

    small_game.max_players = 3
    small_game.save()

    third.refresh_from_db()
    assert not third.is_waitlisted
    assert refreshed(small_game).registered_players == 3


def test_editing_a_confirmed_registration_does_not_waitlist_it(small_game):
    first = register(small_game)
    register(small_game)

    first.comment = "Буду с другом"
    first.save()

    first.refresh_from_db()
    assert not first.is_waitlisted


def test_deleting_the_game_with_registrations_works(small_game):
    register(small_game)
    register(small_game)
    small_game.delete()
    assert GameRegistration.objects.count() == 0


def test_registering_through_the_page_puts_you_on_the_waitlist(client, small_game):
    register(small_game)
    register(small_game)

    response = client.post(
        reverse("game_detail", args=[small_game.id]),
        data={
            "first_name": "Пётр",
            "last_name": "Опоздавший",
            "phone_number": "+79001112233",
            "participation_status": "yes",
            "has_equipment": "yes",
        },
        follow=True,
    )

    assert response.status_code == 200
    registration = GameRegistration.objects.get(phone_number="+79001112233")
    assert registration.is_waitlisted
    assert any(m.level_tag == "warning" for m in response.context["messages"])
    page = response.content.decode()
    assert "⏳" in page


def test_game_page_shows_confirmed_places_not_all_registrations(client, small_game):
    register(small_game)
    register(small_game, status="unknown")
    response = client.get(reverse("game_detail", args=[small_game.id]))
    assert response.context["game"].registered_players == 1
    assert "1/2" in response.content.decode().replace(" ", "").replace("\n", "")
