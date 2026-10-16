import pytest

from main.forms import NewsForm

pytestmark = pytest.mark.django_db


def test_news_form_valid_with_required_fields():
    form = NewsForm(
        data={
            "title": "Заголовок",
            "content": "Содержание новости",
            "is_published": True,
        }
    )
    assert form.is_valid(), form.errors


def test_news_form_invalid_without_title():
    form = NewsForm(
        data={
            "title": "",
            "content": "Содержание новости",
            "is_published": True,
        }
    )
    assert not form.is_valid()
    assert "title" in form.errors


def test_news_form_invalid_without_content():
    form = NewsForm(
        data={
            "title": "Заголовок",
            "content": "",
            "is_published": True,
        }
    )
    assert not form.is_valid()
    assert "content" in form.errors


def test_news_form_is_published_optional_defaults_to_false_when_unchecked():
    """
    Чекбокс не отправляется в data, если он не отмечен — это нормальное
    поведение HTML-форм. Проверяем, что форма всё равно валидна.
    """
    form = NewsForm(
        data={
            "title": "Заголовок",
            "content": "Содержание новости",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["is_published"] is False
