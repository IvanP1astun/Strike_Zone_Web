import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from main.models import News

pytestmark = pytest.mark.django_db

User = get_user_model()


# ---------------------------------------------------------------------------
# Главная страница / лента новостей
# ---------------------------------------------------------------------------

def test_home_page_status_ok(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200


def test_home_page_lists_published_news(client, news_item):
    response = client.get(reverse("home"))
    assert news_item.title in response.content.decode()


def test_home_page_hides_unpublished_news(client, staff_user):
    hidden = News.objects.create(
        title="Черновик", content="...", author=staff_user, is_published=False
    )
    response = client.get(reverse("home"))
    assert hidden.title not in response.content.decode()


# ---------------------------------------------------------------------------
# Создание новости — доступ (main/views.py: NewsCreateView.dispatch)
# ---------------------------------------------------------------------------

def test_news_create_forbidden_for_anonymous(client):
    response = client.get(reverse("news_create"))
    assert response.status_code == 403


def test_news_create_forbidden_for_regular_user(client, user):
    client.force_login(user)
    response = client.get(reverse("news_create"))
    assert response.status_code == 403


def test_news_create_allowed_for_moderator(client, moderator_user):
    client.force_login(moderator_user)
    response = client.get(reverse("news_create"))
    assert response.status_code == 200


def test_news_create_allowed_for_staff(client, staff_user):
    client.force_login(staff_user)
    response = client.get(reverse("news_create"))
    assert response.status_code == 200


def test_news_create_allowed_for_superuser(client, superuser):
    client.force_login(superuser)
    response = client.get(reverse("news_create"))
    assert response.status_code == 200


def test_news_create_sets_author_automatically(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("news_create"),
        data={
            "title": "Новая новость",
            "content": "Текст новости",
            "is_published": True,
        },
    )
    assert response.status_code == 302
    created = News.objects.get(title="Новая новость")
    assert created.author == staff_user


def test_news_create_redirects_to_home_on_success(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("news_create"),
        data={"title": "T", "content": "C", "is_published": True},
    )
    assert response.url == reverse("home")


# ---------------------------------------------------------------------------
# Известный баг: кнопка "Добавить новость" показывается шире, чем реальный
# доступ (main/templates/main/index.html использует user.groups.all,
# а dispatch проверяет группу именно "moderators"). Тест фиксирует текущее
# поведение — если баг поправят, этот тест нужно обновить вместе с ним.
# ---------------------------------------------------------------------------

def test_create_button_visible_for_any_group_member_but_access_denied(client):
    other_group, _ = Group.objects.get_or_create(name="players")
    user = User.objects.create_user(username="random_group_user", password="pass12345")
    user.groups.add(other_group)
    client.force_login(user)

    home_response = client.get(reverse("home"))
    assert "Добавить новость" in home_response.content.decode()

    create_response = client.get(reverse("news_create"))
    assert create_response.status_code == 403
