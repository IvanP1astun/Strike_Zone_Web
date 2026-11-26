from unittest import mock

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_ok(client):
    response = client.get(reverse('health'))
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'ok'}
    assert 'no-cache' in response['Cache-Control']


def test_health_is_public_and_read_only(client):
    assert client.head(reverse('health')).status_code == 200
    assert client.post(reverse('health')).status_code == 405


def test_health_returns_503_when_database_is_down(client):
    with mock.patch('main.views.connection') as connection:
        connection.cursor.side_effect = Exception('db is down')
        response = client.get(reverse('health'))
    assert response.status_code == 503
    assert response.json()['status'] == 'error'
