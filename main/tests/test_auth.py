import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_user_can_register(client):
    response = client.post(
        reverse("register"),
        data={
            "username": "newplayer",
            "first_name": "Пётр",
            "last_name": "Иванов",
            "email": "newplayer@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )
    assert response.status_code == 302
    assert User.objects.filter(username="newplayer").exists()


def test_user_can_login(client, user):
    response = client.post(
        reverse("login"),
        data={"username": user.username, "password": "pass12345"},
    )
    assert response.status_code == 302


def test_login_fails_with_wrong_password(client, user):
    response = client.post(
        reverse("login"),
        data={"username": user.username, "password": "wrong-password"},
    )
    assert response.status_code == 200  # остаёмся на форме логина
    assert not response.wsgi_request.user.is_authenticated
