import calendar as calendar_module
import hmac
import json
import logging
import secrets
from datetime import date, timedelta

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView, CreateView
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.conf import settings
from django.db import connection, models, transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from . import telegram_bot, user_notifications
from .ics import build_calendar
from .models import (
    News,
    Catalog,
    Gun,
    AirsoftEquipment,
    AirsoftGame,
    GunAccessory,
    GunModule,
    GameRegistration,
    Profile,
)

from .forms import (
    NewsForm,
    GameRegistrationForm,
    GameRegistrationEditForm,
    CustomUserCreationForm,
    CustomAuthenticationForm,
    NotificationSettingsForm,
    ProfileForm,
    GameCreateForm,
)

logger = logging.getLogger(__name__)


def home(request):
    """Главная страница с новостями."""
    news_list = News.objects.filter(is_published=True)[:10]
    return render(request, "main/index.html", {"news_list": news_list})


class NewsListView(ListView):
    """Список последних 10-и новостей."""

    model = News
    template_name = "main/index.html"
    context_object_name = "news_list"
    paginate_by = 10

    def get_queryset(self):
        return News.objects.filter(is_published=True)


class NewsCreateView(CreateView):
    """Создание новой новости. Доступно только для админов и модераторов."""

    model = News
    form_class = NewsForm
    template_name = "main/news_form.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        """Проверка: только админы и модераторы"""
        if not (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.groups.filter(name="moderators").exists()
        ):
            return render(request, "main/403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Автоматически устанавливаем автора новости."""
        form.instance.author = self.request.user
        return super().form_valid(form)


def post(request):
    return render(request, "main/post.html")


def rules(request):
    return render(request, "main/rules.html")


def about(request):
    return render(request, "main/about.html")


# =============================================
# РЕГИСТРАЦИЯ И АВТОРИЗАЦИЯ
# =============================================


def register(request):
    """Регистрация нового пользователя"""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _("Регистрация успешно завершена!"))
            return redirect("home")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})


class CustomLoginView(LoginView):
    """Авторизация пользователя"""

    authentication_form = CustomAuthenticationForm
    template_name = "registration/login.html"

    def get_success_url(self):
        return reverse_lazy("home")


class CustomLogoutView(LogoutView):
    """Выход пользователя"""

    next_page = "home"


# =============================================
# КАТАЛОГ
# =============================================


def catalog(request):
    """Страница каталога с разделами (всегда статичные)"""
    sections = [
        {
            "name": _("Страйкбольные игры"),
            "icon": "🎯",
            "description": _("Расписание, сценарии, регистрация на игры"),
            "count": AirsoftGame.objects.filter(is_active=True).count(),
            "url": "catalog_games",
            "color": "#dc3545",
        },
        {
            "name": _("Аксессуары 3D печать"),
            "icon": "🖨️",
            "description": _("Индивидуальные детали, апгрейды, кастом"),
            "count": GunModule.objects.count(),
            "url": "catalog_modules",
            "color": "#fd7e14",
        },
        {
            "name": _("Страйкбольные привода"),
            "icon": "🔫",
            "description": _("AEG, GBB, HPA, снайперские винтовки"),
            "count": Gun.objects.count(),
            "url": "catalog_guns",
            "color": "#198754",
        },
        {
            "name": _("Аксессуары для приводов"),
            "icon": "🧩",
            "description": _("Прицелы, глушители, тактические ручки"),
            "count": GunAccessory.objects.count(),
            "url": "catalog_accessories",
            "color": "#6f42c1",
        },
        {
            "name": _("Страйкбольное оборудование"),
            "icon": "🛡️",
            "description": _("Хронографы, зарядки, аккумуляторы"),
            "count": AirsoftEquipment.objects.count(),
            "url": "catalog_equipment",
            "color": "#0dcaf0",
        },
    ]

    return render(
        request,
        "catalog/catalog.html",
        {
            "sections": sections,
            "total_items": sum(s["count"] for s in sections),
        },
    )


def catalog_detail(request, pk):
    """Страница конкретного каталога (для обратной совместимости)"""
    catalog = get_object_or_404(Catalog, pk=pk)
    return render(request, "catalog/catalog_detail.html", {"catalog": catalog})


def catalog_games(request):
    """Список страйкбольных игр"""
    games = AirsoftGame.objects.filter(is_active=True)
    return render(
        request,
        "catalog/section_list.html",
        {
            "items": games,
            "title": _("Страйкбольные игры"),
            "is_games": True,
            "icon": "🎯",
            "back_url": "catalog",
        },
    )


def catalog_modules(request):
    """Список 3D-печати и модулей"""
    modules = GunModule.objects.all()
    return render(
        request,
        "catalog/section_list.html",
        {
            "items": modules,
            "title": _("Аксессуары 3D печать"),
            "icon": "🖨️",
            "back_url": "catalog",
        },
    )


def catalog_guns(request):
    """Список страйкбольных приводов"""
    guns = Gun.objects.all()
    return render(
        request,
        "catalog/section_list.html",
        {
            "items": guns,
            "title": _("Страйкбольные привода"),
            "icon": "🔫",
            "back_url": "catalog",
        },
    )


def catalog_accessories(request):
    """Список аксессуаров"""
    accessories = GunAccessory.objects.all()
    return render(
        request,
        "catalog/section_list.html",
        {
            "items": accessories,
            "title": _("Аксессуары для приводов"),
            "icon": "🧩",
            "back_url": "catalog",
        },
    )


def catalog_equipment(request):
    """Список оборудования"""
    equipment = AirsoftEquipment.objects.all()
    return render(
        request,
        "catalog/section_list.html",
        {
            "items": equipment,
            "title": _("Страйкбольное оборудование"),
            "icon": "🛡️",
            "back_url": "catalog",
        },
    )


def _waitlist_message(registration):
    return _(
        "⏳ Свободных мест нет: вы в листе ожидания, ваша позиция — %(position)s. "
        "Если место освободится, вы получите его автоматически."
    ) % {"position": registration.waitlist_position}


def game_detail(request, game_id):
    """Детальная страница игры с формой регистрации"""
    game = get_object_or_404(AirsoftGame, id=game_id)
    registrations = game.registrations.all()

    # Получаем параметры фильтрации из GET-запроса
    status_filter = request.GET.get("status", "all")
    search_query = request.GET.get("search", "")

    # Фильтруем по статусу
    if status_filter != "all":
        registrations = registrations.filter(participation_status=status_filter)

    # Фильтруем по поиску (имя, фамилия, позывной, телефон)
    if search_query:
        registrations = registrations.filter(
            models.Q(first_name__icontains=search_query)
            | models.Q(last_name__icontains=search_query)
            | models.Q(callsign__icontains=search_query)
            | models.Q(phone_number__icontains=search_query)
        )
    # Статистика
    yes_count = game.registrations.filter(participation_status="yes").count()
    no_count = game.registrations.filter(participation_status="no").count()
    unknown_count = game.registrations.filter(participation_status="unknown").count()
    waitlist_count = game.registrations.filter(is_waitlisted=True).count()

    # Проверяем, зарегистрирован ли уже пользователь на эту игру
    user_registration = None
    if request.user.is_authenticated:
        user_registration = game.registrations.filter(user=request.user).first()

        if not user_registration and hasattr(request.user, "profile"):
            profile = request.user.profile
            if profile.phone_number:
                user_registration = game.registrations.filter(
                    phone_number=profile.phone_number
                ).first()
                if user_registration:
                    user_registration.user = request.user
                    user_registration.save()

    previous_status = user_registration.participation_status if user_registration else None

    if request.method == "POST":
        if user_registration:
            form = GameRegistrationEditForm(request.POST, instance=user_registration)
            if form.is_valid():
                registration = form.save()
                if registration.participation_status != previous_status:
                    transaction.on_commit(
                        lambda: user_notifications.notify_registration(registration)
                    )
                if registration.is_waitlisted:
                    messages.warning(request, _waitlist_message(registration))
                else:
                    messages.success(request, _("✅ Статус успешно обновлен!"))
                return redirect("game_detail", game_id=game.id)
        else:
            form = GameRegistrationForm(request.POST, user=request.user, game=game)
            if form.is_valid():
                registration = form.save(commit=False)
                registration.game = game
                if request.user.is_authenticated:
                    registration.user = request.user
                registration.save()
                transaction.on_commit(
                    lambda: user_notifications.notify_registration(registration)
                )
                if registration.is_waitlisted:
                    messages.warning(request, _waitlist_message(registration))
                else:
                    messages.success(request, _("✅ Вы успешно зарегистрировались на игру!"))
                return redirect("game_detail", game_id=game.id)
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
    else:
        if user_registration:
            form = GameRegistrationEditForm(instance=user_registration)
        else:
            form = GameRegistrationForm(user=request.user, game=game)

    return render(
        request,
        "catalog/game_detail.html",
        {
            "game": game,
            "registrations": registrations,
            "form": form,
            "user_registration": user_registration,
            "yes_count": yes_count,
            "no_count": no_count,
            "unknown_count": unknown_count,
            "waitlist_count": waitlist_count,
            "total_count": game.registrations.count(),
            "status_filter": status_filter,
            "search_query": search_query,
        },
    )


@login_required
def cancel_registration(request, registration_id):
    """Отмена регистрации на игру"""
    registration = get_object_or_404(
        GameRegistration, id=registration_id, user=request.user
    )
    game_id = registration.game.id
    registration.delete()
    messages.success(request, _("Вы отменили регистрацию на игру"))
    return redirect("game_detail", game_id=game_id)


@login_required
def profile(request):
    """Личный кабинет пользователя"""
    user = request.user

    # Создаем профиль если его нет
    profile, created = Profile.objects.get_or_create(user=user)

    # Получаем регистрации пользователя
    user_registrations = (
        GameRegistration.objects.filter(user=user)
        .select_related("game")
        .order_by("-game__date")
    )

    # Текущие игры (дата >= сегодня)
    upcoming_registrations = user_registrations.filter(
        game__date__gte=timezone.now().date()
    )

    # Прошедшие игры
    past_registrations = user_registrations.filter(game__date__lt=timezone.now().date())

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=user)
        if form.is_valid():
            form.save(user=user)
            messages.success(request, _("Профиль успешно обновлен!"))
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile, user=user)

    return render(
        request,
        "profile/profile.html",
        {
            "profile": profile,
            "form": form,
            "user_registrations": user_registrations,
            "upcoming_registrations": upcoming_registrations,
            "past_registrations": past_registrations,
            "notification_form": NotificationSettingsForm(instance=profile),
            "telegram_bot_username": settings.TELEGRAM_BOT_USERNAME,
        },
    )


# =============================================
# УВЕДОМЛЕНИЯ
# =============================================

@login_required
@require_POST
def notification_settings(request):
    """Сохранить настройки уведомлений (email / Telegram / язык)."""
    profile, _created = Profile.objects.get_or_create(user=request.user)
    form = NotificationSettingsForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, _("Настройки уведомлений сохранены."))
    else:
        messages.error(request, _("Не удалось сохранить настройки уведомлений."))
    return redirect("profile")


@login_required
@require_POST
def telegram_connect(request):
    """Создать одноразовый код привязки Telegram (ссылка на бота покажется в профиле)."""
    profile, _created = Profile.objects.get_or_create(user=request.user)
    if not settings.TELEGRAM_BOT_USERNAME:
        messages.error(request, _("Уведомления в Telegram пока не настроены на сайте."))
    else:
        profile.telegram_link_token = secrets.token_urlsafe(16)
        profile.save(update_fields=["telegram_link_token", "updated_at"])
    return redirect("profile")


@login_required
@require_POST
def telegram_disconnect(request):
    """Отвязать Telegram."""
    profile, _created = Profile.objects.get_or_create(user=request.user)
    profile.telegram_chat_id = None
    profile.telegram_link_token = ""
    profile.save(update_fields=["telegram_chat_id", "telegram_link_token", "updated_at"])
    messages.success(request, _("Telegram отключён."))
    return redirect("profile")


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """Webhook Telegram-бота. Защищён секретным заголовком, который Telegram
    присылает, если секрет передан в setWebhook (команда set_telegram_webhook)."""
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not secret:
        raise Http404
    received = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(received.encode(), secret.encode()):
        return HttpResponse(status=403)
    try:
        update = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)
    try:
        telegram_bot.handle_update(update)
    except Exception:
        # always answer 200, otherwise Telegram keeps re-sending the update
        logger.exception("Telegram webhook failed")
    return HttpResponse("ok")


@login_required
@permission_required('main.can_add_game', raise_exception=True)
def game_create(request):
    """Создание новой игры (только для организаторов)"""
    if request.method == 'POST':
        form = GameCreateForm(request.POST, request.FILES)
        if form.is_valid():
            game = form.save(commit=False)
            game.created_by = request.user
            game.save()
            messages.success(
                request,
                _('✅ Игра "%(name)s" успешно создана!') % {"name": game.name},
            )
            return redirect('game_detail', game_id=game.id)
    else:
        form = GameCreateForm()
    
    return render(request, 'catalog/game_create.html', {
        'form': form,
        'title': _('Создание игры'),
        'icon': '➕',
    })


@require_safe
@never_cache
def health(request):
    """Liveness/readiness probe for Docker and monitoring.

    Returns 200 when the app can reach the database, 503 otherwise.
    It exposes no data, so it is public.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health check failed: database is not reachable")
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})


# =============================================
# КАЛЕНДАРЬ ИГР
# =============================================

CALENDAR_MIN_YEAR = 2000
CALENDAR_MAX_YEAR = 2100


def _month_shift(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def games_calendar(request):
    """Месячный календарь активных игр."""
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        date(year, month, 1)
        if not CALENDAR_MIN_YEAR <= year <= CALENDAR_MAX_YEAR:
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    weeks_dates = calendar_module.Calendar(firstweekday=0).monthdatescalendar(year, month)
    first_day, last_day = weeks_dates[0][0], weeks_dates[-1][-1]
    games = AirsoftGame.objects.filter(
        is_active=True, date__gte=first_day, date__lte=last_day
    ).order_by("date", "name")
    by_day = {}
    for game in games:
        by_day.setdefault(game.date, []).append(game)

    weeks = [
        [
            {
                "date": day,
                "in_month": day.month == month,
                "is_today": day == today,
                "games": by_day.get(day, []),
            }
            for day in week
        ]
        for week in weeks_dates
    ]
    prev_year, prev_month = _month_shift(year, month, -1)
    next_year, next_month = _month_shift(year, month, 1)
    month_games = [g for g in games if g.date.month == month and g.date.year == year]
    return render(
        request,
        "catalog/calendar.html",
        {
            "weeks": weeks,
            "month_date": date(year, month, 1),
            # 2024-01-01 is a Monday: used for localized weekday names
            "weekdays": [date(2024, 1, 1) + timedelta(days=i) for i in range(7)],
            "month_games": month_games,
            "prev": {"year": prev_year, "month": prev_month},
            "next": {"year": next_year, "month": next_month},
            "show_prev": (prev_year, prev_month) >= (CALENDAR_MIN_YEAR, 1),
            "show_next": (next_year, next_month) <= (CALENDAR_MAX_YEAR, 12),
        },
    )


def _ics_response(request, games, filename=None):
    content = build_calendar(
        games,
        url_for=lambda game: request.build_absolute_uri(
            reverse("game_detail", args=[game.id])
        ),
        host=request.get_host(),
    )
    response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    if filename:
        response["Content-Disposition"] = 'attachment; filename="%s"' % filename
    return response


@require_safe
def game_ics(request, game_id):
    """Скачать одну игру как событие календаря (.ics)."""
    game = get_object_or_404(AirsoftGame, id=game_id)
    return _ics_response(request, [game], filename="game-%s.ics" % game.id)


@require_safe
def games_ics_feed(request):
    """Лента предстоящих активных игр для подписки в календаре (.ics)."""
    games = AirsoftGame.objects.filter(
        is_active=True, date__gte=timezone.localdate()
    ).order_by("date", "name")
    return _ics_response(request, games)
