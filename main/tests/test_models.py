import pytest
from datetime import date, timedelta
from django.utils import timezone

from main.models import News, AirsoftGame, GameRegistration

pytestmark = pytest.mark.django_db


def test_news_str_returns_title(news_item):
    assert str(news_item) == "Тестовая новость"


def test_news_default_is_published_true(staff_user):
    news = News.objects.create(title="X", content="Y", author=staff_user)
    assert news.is_published is True


def test_news_ordering_newest_first(staff_user):
    """
    Meta.ordering = ['-created_at'] — новые новости должны идти первыми.
    created_at задаём явно: два create() подряд могут получить одинаковую
    timezone.now() с точностью до микросекунды, и тест станет случайным.
    """
    now = timezone.now()
    first = News.objects.create(
        title="Первая", content="...", author=staff_user,
        created_at=now - timedelta(minutes=1),
    )
    second = News.objects.create(
        title="Вторая", content="...", author=staff_user,
        created_at=now,
    )

    titles = list(News.objects.values_list("title", flat=True))

    assert titles[0] == second.title
    assert titles[1] == first.title


def test_airsoft_game_is_full_property():
    game = AirsoftGame.objects.create(
        name="Полная игра",
        date=date.today() + timedelta(days=1),
        max_players=2,
        registered_players=2,
    )
    assert game.is_full is True
    assert game.places_left == 0


def test_airsoft_game_places_left_when_not_full():
    game = AirsoftGame.objects.create(
        name="Игра со свободными местами",
        date=date.today() + timedelta(days=1),
        max_players=10,
        registered_players=3,
    )
    assert game.is_full is False
    assert game.places_left == 7


def test_game_registration_full_name(airsoft_game):
    reg = GameRegistration.objects.create(
        game=airsoft_game,
        first_name="Иван",
        last_name="Петров",
        phone_number="+79990001122",
    )
    assert reg.full_name == "Петров Иван"


def test_game_str_includes_date(airsoft_game):
    assert str(airsoft_game) == f"{airsoft_game.name} ({airsoft_game.date})"
