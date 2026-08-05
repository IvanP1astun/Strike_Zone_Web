from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from PIL import Image

from .constants import MAX_NAME_LENGTH

User = get_user_model()


class News(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Содержание")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Автор")
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

    def __str__(self):
        return self.title


class Profile(models.Model):
    """Профиль пользователя (расширение User)"""

    # Роли пользователей
    ROLE_CHOICES = [
        ('player', 'Игрок'),
        ('commander', 'Командир'),
        ('admin', 'Администратор'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )

    # Аватар
    avatar = models.ImageField(
        upload_to="avatars/", verbose_name="Аватар", blank=True, null=True
    )

    # День рождения
    birth_date = models.DateField(verbose_name="День рождения", blank=True, null=True)

    # Позывной (уже есть в GameRegistration, но добавим и в профиль)
    callsign = models.CharField(
        max_length=100,
        verbose_name="Позывной",
        blank=True,
        help_text="Ваш позывной на играх",
    )

    # Дополнительная информация
    bio = models.TextField(
        verbose_name="О себе", blank=True, help_text="Краткая информация о себе"
    )

    # Телефон (дублируем для профиля)
    phone_number = models.CharField(
        max_length=20, verbose_name="Номер телефона", blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player',
        verbose_name='Роль'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"Профиль {self.user.username}"

    @property
    def full_name(self):
        """Полное имя пользователя"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.last_name} {self.user.first_name}"
        return self.user.username

    @property
    def avatar_url(self):
        """URL аватарки или заглушка"""
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return "/static/images/default-avatar.png"

    @property
    def can_create_games(self):
        """Может ли пользователь создавать игры"""
        return self.role in ['commander', 'admin']

    def save(self, *args, **kwargs):
        """Оптимизация аватара при сохранении"""
        super().save(*args, **kwargs)

        if self.avatar:
            try:
                img = Image.open(self.avatar.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.avatar.path)
            except Exception:
                pass


class Tag(models.Model):
    """Тэг"""

    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text="Тег",
        verbose_name="Тег",
    )
    slug = models.SlugField(
        unique=True,
        verbose_name="Slug",
        max_length=MAX_NAME_LENGTH,
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Gun(models.Model):
    """Страйбольное оружие"""

    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text="Страйбольное оружие",
        verbose_name="Страйбольное оружие",
    )
    model = models.CharField(max_length=100, verbose_name="Модель", blank=True)
    brand = models.CharField(max_length=100, verbose_name="Бренд", blank=True)
    # НОВЫЕ ПОЛЯ
    description = models.TextField(verbose_name="Описание", blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена", null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name="В наличии")
    image = models.ImageField(
        upload_to="guns/", verbose_name="Изображение", blank=True, null=True
    )

    class Meta:
        verbose_name = "Страйбольное привод"
        verbose_name_plural = "Страйбольные привода"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AirsoftEquipment(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание", blank=True)
    # НОВЫЕ ПОЛЯ
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена", null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name="В наличии")
    image = models.ImageField(
        upload_to="equipment/", verbose_name="Изображение", blank=True, null=True
    )
    category = models.CharField(
        max_length=100,
        verbose_name="Категория",
        blank=True,
        choices=[
            ("chrono", "Хронограф"),
            ("charger", "Зарядное устройство"),
            ("battery", "Аккумулятор"),
            ("other", "Другое"),
        ],
        default="other",
    )

    class Meta:
        verbose_name = "Страйбольное оборудование"
        verbose_name_plural = "Страйбольное оборудование"

    def __str__(self):
        return self.name


class GunAccessory(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    type = models.CharField(max_length=100, verbose_name="Тип аксессуара", blank=True)
    # НОВЫЕ ПОЛЯ
    description = models.TextField(verbose_name="Описание", blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена", null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name="В наличии")
    image = models.ImageField(
        upload_to="accessories/", verbose_name="Изображение", blank=True, null=True
    )

    class Meta:
        verbose_name = "Аксессуар для привода"
        verbose_name_plural = "Аксессуары для приводов"

    def __str__(self):
        return self.name


class GunModule(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание", blank=True)
    file_url = models.URLField(verbose_name="Ссылка на файл", blank=True)
    # НОВЫЕ ПОЛЯ
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена", null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name="В наличии")
    image = models.ImageField(
        upload_to="modules/", verbose_name="Изображение", blank=True, null=True
    )
    material = models.CharField(
        max_length=100,
        verbose_name="Материал",
        blank=True,
        choices=[
            ("pla", "PLA"),
            ("petg", "PETG"),
            ("abs", "ABS"),
            ("nylon", "Нейлон"),
            ("other", "Другое"),
        ],
        default="pla",
    )

    class Meta:
        verbose_name = "3D модуль"
        verbose_name_plural = "3D модули"

    def __str__(self):
        return self.name


class Catalog(models.Model):
    """Каталог"""

    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    tags = models.ManyToManyField("Tag", blank=True, verbose_name="Тэги")
    guns = models.ManyToManyField(
        "Gun", blank=True, verbose_name="Страйбольные привода"
    )
    airsoft_equipment = models.ManyToManyField(
        "AirsoftEquipment", blank=True, verbose_name="Страйбольное оборудование"
    )
    airsoft_games = models.ManyToManyField(
        "AirsoftGame", blank=True, verbose_name="Страйбольные игры"
    )
    guns_accessories = models.ManyToManyField(
        "GunAccessory", blank=True, verbose_name="Страйбольные аксессуары"
    )
    guns_modules = models.ManyToManyField(
        "GunModule", blank=True, verbose_name="Страйбольные модули"
    )

    class Meta:
        verbose_name = "Каталог"
        verbose_name_plural = "Каталоги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AirsoftGame(models.Model):
    """Страйкбольные игры"""

    STATUS_CHOICES = [
        ('upcoming', 'Предстоит'),
        ('ongoing', 'Идёт'),
        ('finished', 'Завершена'),
        ('archived', 'Архивирована'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming',
        verbose_name='Статус'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_games',
        verbose_name='Создатель'
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата архивации'
    )

    def update_status(self):
        """Обновляет статус игры в зависимости от даты"""
        today = timezone.now().date()

        if self.status == 'archived':
            return

        if self.date < today:
            # Игра уже прошла
            if self.status != 'finished':
                self.status = 'finished'
                self.finished_at = timezone.now()
                self.save()

            # Если прошло больше 3 дней - архивируем
            if self.finished_at and (timezone.now() - self.finished_at).days >= 3:
                self.status = 'archived'
                self.archived_at = timezone.now()
                self.is_active = False
                self.save()

        elif self.date == today:
            self.status = 'ongoing'
            self.save()

        else:
            self.status = 'upcoming'
            self.save()

    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text="Страйкбольная игра",
        verbose_name="Страйкбольные игры",
    )
    date = models.DateField(
        verbose_name="Дата игры",
    )
    # НОВЫЕ ПОЛЯ
    description = models.TextField(verbose_name="Описание", blank=True)
    location = models.CharField(
        max_length=200, verbose_name="Место проведения", blank=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Стоимость участия",
        null=True,
        blank=True,
    )
    max_players = models.PositiveIntegerField(
        verbose_name="Максимум игроков", default=30
    )
    registered_players = models.PositiveIntegerField(
        verbose_name="Зарегистрировано игроков", default=0
    )
    image = models.ImageField(
        upload_to="games/", verbose_name="Изображение", blank=True, null=True
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Страйкбольная игра"
        verbose_name_plural = "Страйкбольные игры"
        ordering = ["date"]

    def __str__(self):
        return f"{self.name} ({self.date})"

    @property
    def is_full(self):
        return self.registered_players >= self.max_players

    @property
    def places_left(self):
        return self.max_players - self.registered_players


class GameRegistration(models.Model):
    """Регистрация участника на игру"""
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='game_registrations',
        verbose_name='Пользователь'
    )

    # Статус участия
    STATUS_CHOICES = [
        ("yes", "Да, приеду"),
        ("no", "Нет, не приеду"),
        ("unknown", "Неизвестно"),
    ]

    # Наличие амуниции
    EQUIPMENT_CHOICES = [
        ("yes", "Есть своя"),
        ("no", "Нет, нужна аренда"),
    ]

    game = models.ForeignKey(
        "AirsoftGame",
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name="Игра",
    )

    # Связь с пользователем (опционально - для авторизованных)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="game_registrations",
        verbose_name="Пользователь",
    )

    # Основная информация
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    phone_number = models.CharField(max_length=20, verbose_name="Номер телефона")
    callsign = models.CharField(
        max_length=100,
        verbose_name="Позывной",
        blank=True,
        help_text="Необязательное поле",
    )

    # Статусы
    participation_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="unknown",
        verbose_name="Статус участия",
    )
    has_car = models.BooleanField(default=False, verbose_name="Есть автомобиль")
    has_equipment = models.CharField(
        max_length=10,
        choices=EQUIPMENT_CHOICES,
        default="no",
        verbose_name="Наличие амуниции",
    )

    # Дополнительно
    comment = models.TextField(verbose_name="Комментарий", blank=True)
    registered_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата регистрации"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Регистрация на игру"
        verbose_name_plural = "Регистрации на игры"
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.last_name} {self.first_name} - {self.game.name}"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def can_edit(self):
        """Может ли пользователь редактировать эту регистрацию"""
        if self.user and self.user.is_authenticated:
            return True
        return False


class Favorite(models.Model):
    """Избранное"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="user_favorites",
    )
    airsoft_gun = models.ForeignKey(
        Gun, on_delete=models.CASCADE, verbose_name="Страйбольное оружие"
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["id", "user", "airsoft_gun"],
                name="unique_favorite",
            )
        ]
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные"

    def __str__(self):
        return f"{self.user.username} - {self.airsoft_gun.name}"


class Post(models.Model):
    title = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)


@receiver(pre_save, sender=AirsoftGame)
def game_pre_save(sender, instance, **kwargs):
    """Автоматически обновляет статус перед сохранением"""
    instance.update_status()


def create_groups():
    """Создание групп и прав для пользователей"""
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    # Группа "Организаторы"
    organizer_group, created = Group.objects.get_or_create(name='Организаторы')
    # Права на создание игр
    game_content_type = ContentType.objects.get_for_model(AirsoftGame)
    # Права для игр
    permissions_map = {
        'can_add_game': 'Может добавлять игры',
        'can_change_game': 'Может изменять игры',
        'can_delete_game': 'Может удалять игры',
        'can_view_game': 'Может просматривать игры',
    }
    for codename, name in permissions_map.items():
        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            name=name,
            content_type=game_content_type
        )
        organizer_group.permissions.add(permission)
    # Добавляем права на просмотр профилей (если нужно)
    profile_content_type = ContentType.objects.get_for_model(Profile)
    view_profile_permission, _ = Permission.objects.get_or_create(
        codename='can_view_profile',
        name='Может просматривать профили',
        content_type=profile_content_type
    )
    organizer_group.permissions.add(view_profile_permission)
    return organizer_group
