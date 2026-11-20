"""Interface language: Russian (default), English and Japanese."""
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import get_template
from django.urls import reverse
from django.utils import translation

pytestmark = pytest.mark.django_db

TEMPLATES_DIR = Path(settings.BASE_DIR) / 'main' / 'templates'
TEMPLATE_NAMES = sorted(
    path.relative_to(TEMPLATES_DIR).as_posix() for path in TEMPLATES_DIR.rglob('*.html')
)

# The heading of the rules page in every language.
RULES_HEADING = {
    'ru': 'Наши правила',
    'en': 'Our rules',
    'ja': '私たちのルール',
}


@pytest.mark.parametrize('name', TEMPLATE_NAMES)
def test_every_template_compiles(name):
    get_template(name)


def test_languages_configured():
    assert [code for code, _name in settings.LANGUAGES] == ['ru', 'en', 'ja']
    assert settings.LANGUAGE_CODE == 'ru'


def test_default_language_is_russian(client):
    response = client.get(reverse('rules'))
    assert response.status_code == 200
    assert RULES_HEADING['ru'] in response.content.decode()
    assert '<html lang="ru">' in response.content.decode()


@pytest.mark.parametrize('code', ['en', 'ja'])
def test_accept_language_header(client, code):
    response = client.get(reverse('rules'), headers={'accept-language': code})
    content = response.content.decode()
    assert RULES_HEADING[code] in content
    assert RULES_HEADING['ru'] not in content
    assert '<html lang="%s">' % code in content


@pytest.mark.parametrize('code', ['ru', 'en', 'ja'])
def test_language_switcher_sets_cookie_and_redirects(client, code):
    response = client.post(
        reverse('set_language'), {'language': code, 'next': reverse('rules')}
    )
    assert response.status_code == 302
    assert response.url == reverse('rules')
    assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == code

    page = client.get(reverse('rules'))
    assert RULES_HEADING[code] in page.content.decode()


def test_cookie_wins_over_browser_language(client):
    client.post(reverse('set_language'), {'language': 'ja', 'next': '/'})
    response = client.get(reverse('rules'), headers={'accept-language': 'en'})
    assert RULES_HEADING['ja'] in response.content.decode()


def test_unknown_language_is_ignored(client):
    client.post(reverse('set_language'), {'language': 'xx', 'next': '/'})
    assert settings.LANGUAGE_COOKIE_NAME not in client.cookies
    response = client.get(reverse('rules'))
    assert RULES_HEADING['ru'] in response.content.decode()


def test_switcher_lists_all_languages(client):
    content = client.get(reverse('rules')).content.decode()
    assert reverse('set_language') in content
    for label in ('Русский', 'English', '日本語'):
        assert label in content


def test_open_redirect_is_not_followed(client):
    response = client.post(
        reverse('set_language'), {'language': 'en', 'next': 'https://evil.example/'}
    )
    assert response.status_code == 302
    assert response.url == '/'


def test_lazy_model_strings_follow_active_language():
    from main.models import News

    label = News._meta.verbose_name_plural
    with translation.override('ru'):
        assert str(label) == 'Новости'
    with translation.override('en'):
        assert str(label) == 'News'
    with translation.override('ja'):
        assert str(label) == 'ニュース'


def test_every_language_has_a_complete_catalog():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        'translations_tool', Path(settings.BASE_DIR) / 'scripts' / 'translations.py'
    )
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    assert tool.cmd_check() == 0
