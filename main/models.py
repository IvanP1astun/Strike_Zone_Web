from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Q, UniqueConstraint
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from PIL import Image
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from . import user_notifications
from .constants import MAX_NAME_LENGTH

User = get_user_model()


class News(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Заголовок"))
    content = models.TextField(verbose_name=_("Содержание"))
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Автор"))
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Дата создания")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    is_published = models.BooleanField(default=True, verbose_name=_("Опубликовано"))

    image = models.ImageField(
        upload_to="news/",
        verbose_name=_("Изображение"),
        blank=True,
        null=True,
        help_text=_("Загрузите картинку к новости (необязательно)")
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Новость")
        verbose_name_plural = _("Новости")

    def __str__(self):
        return self.title


class Profile(models.Model):
    """Профиль пользователя (расширение User)"""

    # Роли пользователей
    ROLE_CHOICES = [
        ('player', _('Игрок')),
        ('commander', _('Командир')),
        ('admin', _('Администратор')),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("Пользователь"),
    )

    # Аватар
    avatar = models.ImageField(
        upload_to="avatars/", verbose_name=_("Аватар"), blank=True, null=True
    )

    # День рождения
    birth_date = models.DateField(verbose_name=_("День рождения"), blank=True, null=True)

    # Позывной (уже есть в GameRegistration, но добавим и в профиль)
    callsign = models.CharField(
        max_length=100,
        verbose_name=_("Позывной"),
        blank=True,
        help_text=_("Ваш позывной на играх"),
    )

    # Дополнительная информация
    bio = models.TextField(
        verbose_name=_("О себе"), blank=True, help_text=_("Краткая информация о себе")
    )

    # Телефон (дублируем для профиля)
    phone_number = models.CharField(
        max_length=20, verbose_name=_("Номер телефона"), blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player',
        verbose_name=_('Роль')
    )

    # Уведомления
    notify_email = models.BooleanField(
        default=True, verbose_name=_("Уведомления на email")
    )
    notify_telegram = models.BooleanField(
        default=True, verbose_name=_("Уведомления в Telegram")
    )
    notification_language = models.CharField(
        max_length=8, default="ru", verbose_name=_("Язык уведомлений")
    )
    telegram_chat_id = models.BigIntegerField(
        null=True, blank=True, unique=True, verbose_name="Telegram chat ID"
    )
    telegram_link_token = models.CharField(
        max_length=64, blank=True, default="", verbose_name="Telegram link token"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Профиль пользователя")
        verbose_name_plural = _("Профили пользователей")

    def __str__(self):
        return _("Профиль %(username)s") % {"username": self.user.username}

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
        help_text=_("Тег"),
        verbose_name=_("Тег"),
    )
    slug = models.SlugField(
        unique=True,
        verbose_name="Slug",
        max_length=MAX_NAME_LENGTH,
    )

    class Meta:
        verbose_name = _("Тег")
        verbose_name_plural = _("Теги")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Gun(models.Model):
    """Страйбольное оружие"""

    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text=_("Страйбольное оружие"),
        verbose_name=_("Страйбольное оружие"),
    )
    model = models.CharField(max_length=100, verbose_name=_("Модель"), blank=True)
    brand = models.CharField(max_length=100, verbose_name=_("Бренд"), blank=True)
    # НОВЫЕ ПОЛЯ
    description = models.TextField(verbose_name=_("Описание"), blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Цена"), null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name=_("В наличии"))
    image = models.ImageField(
        upload_to="guns/", verbose_name=_("Изображение"), blank=True, null=True
    )

    class Meta:
        verbose_name = _("Страйбольное привод")
        verbose_name_plural = _("Страйбольные привода")
        ordering = ["name"]

    def __str__(self):
        return self.name


class AirsoftEquipment(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Название"))
    description = models.TextField(verbose_name=_("Описание"), blank=True)
    # НОВЫЕ ПОЛЯ
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Цена"), null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name=_("В наличии"))
    image = models.ImageField(
        upload_to="equipment/", verbose_name=_("Изображение"), blank=True, null=True
    )
    category = models.CharField(
        max_length=100,
        verbose_name=_("Категория"),
        blank=True,
        choices=[
            ("chrono", _("Хронограф")),
            ("charger", _("Зарядное устройство")),
            ("battery", _("Аккумулятор")),
            ("other", _("Другое")),
        ],
        default="other",
    )

    class Meta:
        verbose_name = _("Страйбольное оборудование")
        verbose_name_plural = _("Страйбольное оборудование")

    def __str__(self):
        return self.name


class GunAccessory(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Название"))
    type = models.CharField(max_length=100, verbose_name=_("Тип аксессуара"), blank=True)
    # НОВЫЕ ПОЛЯ
    description = models.TextField(verbose_name=_("Описание"), blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Цена"), null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name=_("В наличии"))
    image = models.ImageField(
        upload_to="accessories/", verbose_name=_("Изображение"), blank=True, null=True
    )

    class Meta:
        verbose_name = _("Аксессуар для привода")
        verbose_name_plural = _("Аксессуары для приводов")

    def __str__(self):
        return self.name


class GunModule(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Название"))
    description = models.TextField(verbose_name=_("Описание"), blank=True)
    file_url = models.URLField(verbose_name=_("Ссылка на файл"), blank=True)
    # НОВЫЕ ПОЛЯ
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Цена"), null=True, blank=True
    )
    in_stock = models.BooleanField(default=True, verbose_name=_("В наличии"))
    image = models.ImageField(
        upload_to="modules/", verbose_name=_("Изображение"), blank=True, null=True
    )
    material = models.CharField(
        max_length=100,
        verbose_name=_("Материал"),
        blank=True,
        choices=[
            ("pla", "PLA"),
            ("petg", "PETG"),
            ("abs", "ABS"),
            ("nylon", _("Нейлон")),
            ("other", _("Другое")),
        ],
        default="pla",
    )

    class Meta:
        verbose_name = _("3D модуль")
        verbose_name_plural = _("3D модули")

    def __str__(self):
        return self.name


class Catalog(models.Model):
    """Каталог"""

    name = models.CharField(max_length=200, verbose_name=_("Название"))
    description = models.TextField(verbose_name=_("Описание"))
    tags = models.ManyToManyField("Tag", blank=True, verbose_name=_("Тэги"))
    guns = models.ManyToManyField(
        "Gun", blank=True, verbose_name=_("Страйбольные привода")
    )
    airsoft_equipment = models.ManyToManyField(
        "AirsoftEquipment", blank=True, verbose_name=_("Страйбольное оборудование")
    )
    airsoft_games = models.ManyToManyField(
        "AirsoftGame", blank=True, verbose_name=_("Страйбольные игры")
    )
    guns_accessories = models.ManyToManyField(
        "GunAccessory", blank=True, verbose_name=_("Страйбольные аксессуары")
    )
    guns_modules = models.ManyToManyField(
        "GunModule", blank=True, verbose_name=_("Страйбольные модули")
    )

    class Meta:
        verbose_name = _("Каталог")
        verbose_name_plural = _("Каталоги")
        ordering = ["name"]

    def __str__(self):
        return self.name


class AirsoftGame(models.Model):
    """Страйкбольные игры"""

    STATUS_CHOICES = [
        ('upcoming', _('Предстоит')),
        ('ongoing', _('Идёт')),
        ('finished', _('Завершена')),
        ('archived', _('Архивирована')),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming',
        verbose_name=_('Статус')
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_games',
        verbose_name=_('Создатель')
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата завершения')
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата архивации')
    )

    def update_status(self):
        """Обновляет статус игры в зависимости от даты"""
        today = timezone.now().date()
        if self.status == 'archived':
            return

        # Временно отключаем сигналы
        if self.date < today:
            if self.status != 'finished':
                self.status = 'finished'
                self.finished_at = timezone.now()
            if self.finished_at and (timezone.now() - self.finished_at).days >= 3:
                self.status = 'archived'
                self.archived_at = timezone.now()
                self.is_active = False
        elif self.date == today:
            self.status = 'ongoing'
        else:
            self.status = 'upcoming'

    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        unique=True,
        help_text=_("Страйкбольная игра"),
        verbose_name=_("Страйкбольные игры"),
    )
    date = models.DateField(
        verbose_name=_("Дата игры"),
    )
    # НОВЫЕ ПОЛЯ
    description = models.TextField(verbose_name=_("Описание"), blank=True)
    location = models.CharField(
        max_length=200, verbose_name=_("Место проведения"), blank=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Стоимость участия"),
        null=True,
        blank=True,
    )
    max_players = models.PositiveIntegerField(
        verbose_name=_("Максимум игроков"), default=30
    )
    registered_players = models.PositiveIntegerField(
        verbose_name=_("Зарегистрировано игроков"), default=0
    )
    image = models.ImageField(
        upload_to="games/", verbose_name=_("Изображение"), blank=True, null=True
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Активна"))
    reminder_sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Напоминание отправлено")
    )

    class Meta:
        verbose_name = _("Страйкбольная игра")
        verbose_name_plural = _("Страйкбольные игры")
        ordering = ["date"]

    def __str__(self):
        return f"{self.name} ({self.date})"

    @property
    def is_full(self):
        return self.registered_players >= self.max_players

    @property
    def places_left(self):
        return max(self.max_players - self.registered_players, 0)

    def confirmed_registrations(self):
        """Registrations that occupy a place: they will come and are not waiting."""
        return self.registrations.filter(
            participation_status="yes", is_waitlisted=False
        )

    def promote_from_waitlist(self):
        """Move people from the waiting list into free places (oldest first).

        Returns the list of promoted registrations (useful for notifications).
        """
        free = self.max_players - self.confirmed_registrations().count()
        if free <= 0:
            return []
        waiting = list(
            self.registrations.filter(is_waitlisted=True, participation_status="yes")
            .order_by("waitlisted_at", "pk")[:free]
        )
        if waiting:
            GameRegistration.objects.filter(pk__in=[r.pk for r in waiting]).update(
                is_waitlisted=False, waitlisted_at=None
            )
        return waiting

    def sync_registered_players(self):
        """Keep the stored counter equal to the number of confirmed places."""
        count = self.confirmed_registrations().count()
        AirsoftGame.objects.filter(pk=self.pk).update(registered_players=count)
        self.registered_players = count

    def rebalance(self):
        """Fill free places from the waiting list and refresh the counter."""
        promoted = self.promote_from_waitlist()
        self.sync_registered_players()
        return promoted


@receiver(pre_save, sender=AirsoftGame)
def game_pre_save(sender, instance, **kwargs):
    """Перед сохранением проставляет актуальный статус игры
    и запоминает, изменились ли дата или место (для уведомлений)."""
    instance.update_status()
    instance._notify_changes = {}
    if instance.pk:
        old = (
            AirsoftGame.objects.filter(pk=instance.pk)
            .values("date", "location")
            .first()
        )
        if old:
            if old["date"] != instance.date:
                instance._notify_changes["date"] = old["date"]
                # the game moved: the reminder has to be sent again
                instance.reminder_sent_at = None
            if old["location"] != instance.location:
                instance._notify_changes["location"] = old["location"]


class GameRegistration(models.Model):
    """Регистрация участника на игру"""
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='game_registrations',
        verbose_name=_('Пользователь')
    )

    # Статус участия
    STATUS_CHOICES = [
        ("yes", _("Да, приеду")),
        ("no", _("Нет, не приеду")),
        ("unknown", _("Неизвестно")),
    ]

    # Наличие амуниции
    EQUIPMENT_CHOICES = [
        ("yes", _("Есть своя")),
        ("no", _("Нет, нужна аренда")),
    ]

    game = models.ForeignKey(
        "AirsoftGame",
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name=_("Игра"),
    )

    # Связь с пользователем (опционально - для авторизованных)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="game_registrations",
        verbose_name=_("Пользователь"),
    )

    # Основная информация
    first_name = models.CharField(max_length=100, verbose_name=_("Имя"))
    last_name = models.CharField(max_length=100, verbose_name=_("Фамилия"))
    phone_number = models.CharField(max_length=20, verbose_name=_("Номер телефона"))
    callsign = models.CharField(
        max_length=100,
        verbose_name=_("Позывной"),
        blank=True,
        help_text=_("Необязательное поле"),
    )

    # Статусы
    participation_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="unknown",
        verbose_name=_("Статус участия"),
    )
    has_car = models.BooleanField(default=False, verbose_name=_("Есть автомобиль"))
    has_equipment = models.CharField(
        max_length=10,
        choices=EQUIPMENT_CHOICES,
        default="no",
        verbose_name=_("Наличие амуниции"),
    )

    # Отметка организатора после игры: None - не отмечено, True - пришёл, False - не пришёл
    attended = models.BooleanField(
        null=True, blank=True, verbose_name=_("Присутствовал")
    )

    # Лист ожидания: «приеду», но свободных мест нет
    is_waitlisted = models.BooleanField(
        default=False, verbose_name=_("В листе ожидания")
    )
    waitlisted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("В очереди с")
    )

    # Дополнительно
    comment = models.TextField(verbose_name=_("Комментарий"), blank=True)
    registered_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Дата регистрации")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Регистрация на игру")
        verbose_name_plural = _("Регистрации на игры")
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.last_name} {self.first_name} - {self.game.name}"

    def save(self, *args, **kwargs):
        """Decide whether this registration gets a place or goes to the waiting list.

        The game row is locked so that two people cannot take the last place
        at the same time (PostgreSQL; SQLite serialises writes anyway).
        """
        with transaction.atomic():
            game = AirsoftGame.objects.select_for_update().get(pk=self.game_id)
            if self.participation_status != "yes":
                # Not coming / unknown: leaves the queue and holds no place.
                self.is_waitlisted = False
                self.waitlisted_at = None
            elif not self.is_waitlisted:
                taken = game.confirmed_registrations()
                if self.pk:
                    taken = taken.exclude(pk=self.pk)
                if taken.count() >= game.max_players:
                    self.is_waitlisted = True
                    self.waitlisted_at = timezone.now()
            super().save(*args, **kwargs)

    @property
    def waitlist_position(self):
        """1-based position in the waiting list, or None if not waiting."""
        if not self.is_waitlisted:
            return None
        waiting = self.game.registrations.filter(
            is_waitlisted=True, participation_status="yes"
        )
        if self.waitlisted_at is None:  # set by hand in the admin
            return waiting.filter(pk__lt=self.pk).count() + 1
        ahead = waiting.filter(
            Q(waitlisted_at__lt=self.waitlisted_at)
            | Q(waitlisted_at=self.waitlisted_at, pk__lt=self.pk)
        )
        return ahead.count() + 1

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def can_edit(self):
        """Может ли пользователь редактировать эту регистрацию"""
        if self.user and self.user.is_authenticated:
            return True
        return False


def _notify_promoted(promoted):
    """Tell people who just got a place from the waiting list (after commit)."""
    if promoted:
        transaction.on_commit(
            lambda: [user_notifications.notify_promoted(r) for r in promoted]
        )


@receiver(post_save, sender=GameRegistration)
@receiver(post_delete, sender=GameRegistration)
def registration_changed(sender, instance, **kwargs):
    """A place was taken or freed: fill it from the waiting list, refresh the counter."""
    if kwargs.get("raw"):
        return
    game = AirsoftGame.objects.filter(pk=instance.game_id).first()
    if game is not None:
        _notify_promoted(game.rebalance())


@receiver(post_save, sender=AirsoftGame)
def game_changed(sender, instance, created=False, **kwargs):
    """max_players may have been raised, the date or place may have changed."""
    if kwargs.get("raw"):
        return
    promoted = instance.promote_from_waitlist()
    if promoted:
        instance.sync_registered_players()
        _notify_promoted(promoted)
    changes = getattr(instance, "_notify_changes", None)
    if changes and not created:
        transaction.on_commit(
            lambda: user_notifications.notify_game_changed(instance, changes)
        )


@receiver(pre_delete, sender=AirsoftGame)
def game_deleted(sender, instance, **kwargs):
    """Deleting a game cancels it: warn the people who were going to come."""
    recipients = user_notifications.recipients_of(instance)
    name, game_date = instance.name, instance.date
    if recipients:
        transaction.on_commit(
            lambda: user_notifications.notify_game_cancelled(name, game_date, recipients)
        )


class Favorite(models.Model):
    """Избранное"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Пользователь"),
        related_name="user_favorites",
    )
    airsoft_gun = models.ForeignKey(
        Gun, on_delete=models.CASCADE, verbose_name=_("Страйбольное оружие")
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["id", "user", "airsoft_gun"],
                name="unique_favorite",
            )
        ]
        verbose_name = _("Избранное")
        verbose_name_plural = _("Избранные")

    def __str__(self):
        return f"{self.user.username} - {self.airsoft_gun.name}"


class Post(models.Model):
    title = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)


def create_groups():
    """Создание групп и прав для пользователей"""
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
        permission, _created = Permission.objects.get_or_create(
            codename=codename,
            name=name,
            content_type=game_content_type
        )
        organizer_group.permissions.add(permission)
    # Добавляем права на просмотр профилей (если нужно)
    profile_content_type = ContentType.objects.get_for_model(Profile)
    view_profile_permission, _created = Permission.objects.get_or_create(
        codename='can_view_profile',
        name='Может просматривать профили',
        content_type=profile_content_type
    )
    organizer_group.permissions.add(view_profile_permission)
    return organizer_group
