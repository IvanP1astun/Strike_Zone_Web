"""Game calendar page and .ics export."""
from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from main.ics import build_calendar, escape_text, fold
from main.models import AirsoftGame

pytestmark = pytest.mark.django_db


@pytest.fixture
def game(db):
    return AirsoftGame.objects.create(
        name="Операция, Шторм",
        date=date.today() + timedelta(days=10),
        location="Лес; Подмосковье",
        description="Строки\nописания",
        price=500,
        max_players=20,
    )


# ---------------------------------------------------------------- ics module

def test_escape_text():
    assert escape_text("a;b,c\\d\ne") == "a\\;b\\,c\\\\d\\ne"


def test_fold_limits_line_length_without_breaking_characters():
    line = "SUMMARY:" + "Ж" * 80
    folded = fold(line)
    parts = folded.split("\r\n")
    assert all(len(part.encode("utf-8")) <= 75 for part in parts)
    assert all(part.startswith(" ") for part in parts[1:])
    assert folded.replace("\r\n ", "") == line


def test_build_calendar_structure(game):
    text = build_calendar(
        [game], url_for=lambda g: "https://example.com/g/%s/" % g.id, host="example.com"
    )
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "UID:game-%s@example.com" % game.id in text
    assert "DTSTART;VALUE=DATE:%s" % game.date.strftime("%Y%m%d") in text
    end = (game.date + timedelta(days=1)).strftime("%Y%m%d")
    assert "DTEND;VALUE=DATE:%s" % end in text
    assert "SUMMARY:Операция\\, Шторм" in text
    assert "LOCATION:Лес\\; Подмосковье" in text
    assert text.count("BEGIN:VEVENT") == text.count("END:VEVENT") == 1
    assert "\n" not in text.replace("\r\n", "")


# --------------------------------------------------------------------- views

def test_single_game_ics_download(client, game):
    response = client.get(reverse("game_ics", args=[game.id]))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    assert "attachment" in response["Content-Disposition"]
    body = response.content.decode("utf-8")
    assert "SUMMARY:Операция\\, Шторм" in body
    assert reverse("game_detail", args=[game.id]) in body


def test_unknown_game_ics_is_404(client):
    assert client.get(reverse("game_ics", args=[99999])).status_code == 404


def test_feed_contains_only_upcoming_active_games(client, game):
    AirsoftGame.objects.create(
        name="Старая игра", date=date.today() - timedelta(days=20), max_players=5
    )
    AirsoftGame.objects.create(
        name="Скрытая игра", date=date.today() + timedelta(days=3), max_players=5,
        is_active=False,
    )
    response = client.get(reverse("games_ics_feed"))
    body = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Шторм" in body
    assert "Старая игра" not in body
    assert "Скрытая игра" not in body


def test_calendar_page_shows_game_in_its_month(client, game):
    url = reverse("games_calendar")
    response = client.get(
        url, {"year": game.date.year, "month": game.date.month}
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert reverse("game_detail", args=[game.id]) in content
    assert reverse("game_ics", args=[game.id]) in content


def test_calendar_defaults_to_current_month(client):
    response = client.get(reverse("games_calendar"))
    today = timezone.localdate()
    assert response.context["month_date"] == date(today.year, today.month, 1)
    assert all(len(week) == 7 for week in response.context["weeks"])


@pytest.mark.parametrize(
    "params",
    [{"year": "abc"}, {"month": "13"}, {"month": "0"}, {"year": "99999"}, {"year": "1"}],
)
def test_calendar_ignores_invalid_month(client, params):
    response = client.get(reverse("games_calendar"), params)
    today = timezone.localdate()
    assert response.status_code == 200
    assert response.context["month_date"] == date(today.year, today.month, 1)


def test_calendar_navigation_wraps_the_year(client):
    response = client.get(reverse("games_calendar"), {"year": 2026, "month": 1})
    assert response.context["prev"] == {"year": 2025, "month": 12}
    response = client.get(reverse("games_calendar"), {"year": 2026, "month": 12})
    assert response.context["next"] == {"year": 2027, "month": 1}


def test_calendar_is_translated(client):
    page = client.get(reverse("games_calendar"), headers={"accept-language": "ja"})
    assert "ゲームカレンダー" in page.content.decode("utf-8")


def test_game_page_has_add_to_calendar_button(client, game):
    page = client.get(reverse("game_detail", args=[game.id]))
    assert reverse("game_ics", args=[game.id]) in page.content.decode("utf-8")
