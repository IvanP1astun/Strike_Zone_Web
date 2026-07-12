from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
from django.core.validators import (
    RegexValidator,
    MaxLengthValidator
)
from django.utils.text import Truncator
from django.db.models import UniqueConstraint


from main.constants import (
    MAX_NAME_LENGTH,
    TRUNCATE_TEXT,
    MAX_ROLE_LENGTH,
    MAX_CONFIRMATION_LENGTH
)


class User(AbstractUser):
    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    ROLE_CHOICES = [
        (USER, 'User'),
        (MODERATOR, 'Moderator'),
        (ADMIN, 'Admin'),
    ]
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+\Z',
                message='Username содержит недопустимые символы!'
            ),
            MaxLengthValidator(
                150,
                message='Username не длиннее 150 символов!'
            )
        ]
    )
    email = models.EmailField(
        unique=True,
        validators=[MaxLengthValidator(254)]
    )
    first_name = models.CharField(max_length=MAX_NAME_LENGTH, blank=True)
    last_name = models.CharField(max_length=MAX_NAME_LENGTH, blank=True)
    bio = models.TextField(blank=True)
    role = models.CharField(
        max_length=MAX_ROLE_LENGTH,
        choices=ROLE_CHOICES,
        default=USER
    )
    confirmation_code = models.CharField(
        max_length=MAX_CONFIRMATION_LENGTH,
        blank=True,
        null=True,
        verbose_name='Код подтверждения'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )
    favorites = models.ManyToManyField(
        'food.Recipe',
        through='food.Favorite',
        related_name='favorited_by_users',
        blank=True,
        verbose_name='Избранные рецепты'
    )

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_sha256'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.role == self.ADMIN or self.is_superuser

    @property
    def is_moderator(self):
        return self.role == self.MODERATOR

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['id']

    def __str__(self):
        """
        Возвращает строковое представление пользователя,
        сокращенное до 30 символов.
        """
        return Truncator(self.username).chars(TRUNCATE_TEXT)


class Subscribers(models.Model):
    """Подписчики"""
    user = models.ForeignKey(
        User,
        related_name='follower',
        on_delete=models.CASCADE,
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='author',
        verbose_name='Автор'
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'author'],
                name='user_author_unique'
            )
        ]

    def __str__(self):
        return f'Пользователь {self.user}, теперь подписан на ({self.author})'
