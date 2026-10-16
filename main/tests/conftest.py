"""
Общие фикстуры для тестов приложения main.
Кладутся в main/tests/conftest.py — pytest подхватывает их автоматически
для всех тестов в этой папке, без явного импорта.
"""
import pytest
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from main.models import News, AirsoftGame

User = get_user_model()


@pytest.fixture
def user(db):
    """Обычный зарегистрированный пользователь без особых прав."""
    return User.objects.create_user(username="player1", password="pass12345")


@pytest.fixture
def staff_user(db):
    """Пользователь с is_staff=True (доступ к созданию новостей по текущей логике)."""
    return User.objects.create_user(
        username="staffer", password="pass12345", is_staff=True
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="boss", password="pass12345", email="boss@example.com"
    )


@pytest.fixture
def moderator_user(db):
    """Обычный пользователь, но состоящий в группе 'moderators'."""
    user = User.objects.create_user(username="moderator1", password="pass12345")
    group, _ = Group.objects.get_or_create(name="moderators")
    user.groups.add(group)
    return user


@pytest.fixture
def news_item(db, staff_user):
    return News.objects.create(
        title="Тестовая новость", content="Текст новости", author=staff_user
    )


@pytest.fixture
def airsoft_game(db):
    return AirsoftGame.objects.create(
        name="Операция Шторм",
        date=date.today() + timedelta(days=7),
        max_players=20,
    )
