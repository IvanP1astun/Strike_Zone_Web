from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone

from .constants import MAX_NAME_LENGTH

User = get_user_model()


class News(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Содержание')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубликовано'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return self.title


class Tag(models.Model):
    """Тэг"""
    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text='Тег',
        verbose_name='Тег',
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='Slug',
        max_length=MAX_NAME_LENGTH,
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Gun(models.Model):
    """Страйбольное оружие"""
    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text='Страйбольное оружие',
        verbose_name='Страйбольное оружие',
    )
    model = models.CharField(
        max_length=100,
        verbose_name='Модель',
        blank=True
    )
    brand = models.CharField(
        max_length=100,
        verbose_name='Бренд',
        blank=True
    )

    class Meta:
        verbose_name = 'Страйбольное привод'
        verbose_name_plural = 'Страйбольные привода'
        ordering = ['name']

    def __str__(self):
        return self.name


class AirsoftEquipment(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )

    class Meta:
        verbose_name = 'Страйбольное оборудование'
        verbose_name_plural = 'Страйбольное оборудование'

    def __str__(self):
        return self.name


class GunAccessory(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    type = models.CharField(
        max_length=100,
        verbose_name='Тип аксессуара',
        blank=True
    )

    class Meta:
        verbose_name = 'Аксессуар для привода'
        verbose_name_plural = 'Аксессуары для приводов'

    def __str__(self):
        return self.name


class GunModule(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание', blank=True)
    file_url = models.URLField(
        verbose_name='Ссылка на файл',
        blank=True
    )

    class Meta:
        verbose_name = '3D модуль'
        verbose_name_plural = '3D модули'

    def __str__(self):
        return self.name


class Catalog(models.Model):
    """Каталог"""
    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    tags = models.ManyToManyField(
        'Tag',
        blank=True,
        verbose_name='Тэги'
    )
    guns = models.ManyToManyField(
        'Gun', blank=True,
        verbose_name='Страйбольные привода'
    )
    airsoft_equipment = models.ManyToManyField(
        'AirsoftEquipment',
        blank=True,
        verbose_name='Страйбольное оборудование'
    )
    airsoft_games = models.ManyToManyField(
        'AirsoftGame',
        blank=True,
        verbose_name='Страйбольные игры'
    )
    guns_accessories = models.ManyToManyField(
        'GunAccessory',
        blank=True,
        verbose_name='Страйбольные аксессуары'
    )
    guns_modules = models.ManyToManyField(
        'GunModule',
        blank=True,
        verbose_name='Страйбольные модули'
    )

    class Meta:
        verbose_name = 'Каталог'
        verbose_name_plural = 'Каталоги'
        ordering = ['name']

    def __str__(self):
        return self.name


class AirsoftGame(models.Model):
    """Страйкбольные игры"""
    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text='Страйкбольная игра',
        verbose_name='Страйкбольные игры',
    )
    date = models.DateField(
        verbose_name='Дата игры',
    )

    class Meta:
        verbose_name = 'Страйкбольная игра'
        verbose_name_plural = 'Страйкбольные игры'
        ordering = ['date']

    def __str__(self):
        return self.name


class Favorite(models.Model):
    """Избранное"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='user_favorites'
    )
    airsoft_gun = models.ForeignKey(
        Gun,
        on_delete=models.CASCADE,
        verbose_name='Страйбольное оружие'
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['id', 'user', 'airsoft_gun'],
                name='unique_favorite',
            )
        ]
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'

    def __str__(self):
        return f"{self.user.username} - {self.airsoft_gun.name}"


class Post(models.Model):
    title = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)
