from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.utils import timezone

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
    ProfileForm,
)


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
            messages.success(request, "Регистрация успешно завершена!")
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
    """Страница каталога с разделами"""
    sections = []

    games = AirsoftGame.objects.filter(is_active=True)
    if games:
        sections.append(
            {
                "name": "Страйкбольные игры",
                "icon": "🎯",
                "description": "Расписание, сценарии, регистрация на игры",
                "count": games.count(),
                "url": "catalog_games",
                "color": "#dc3545",
            }
        )

    modules = GunModule.objects.all()
    if modules:
        sections.append(
            {
                "name": "Аксессуары 3D печать",
                "icon": "🖨️",
                "description": "Индивидуальные детали, апгрейды, кастом",
                "count": modules.count(),
                "url": "catalog_modules",
                "color": "#fd7e14",
            }
        )

    guns = Gun.objects.all()
    if guns:
        sections.append(
            {
                "name": "Страйкбольные привода",
                "icon": "🔫",
                "description": "AEG, GBB, HPA, снайперские винтовки",
                "count": guns.count(),
                "url": "catalog_guns",
                "color": "#198754",
            }
        )

    accessories = GunAccessory.objects.all()
    if accessories:
        sections.append(
            {
                "name": "Аксессуары для приводов",
                "icon": "🧩",
                "description": "Прицелы, глушители, тактические ручки",
                "count": accessories.count(),
                "url": "catalog_accessories",
                "color": "#6f42c1",
            }
        )

    equipment = AirsoftEquipment.objects.all()
    if equipment:
        sections.append(
            {
                "name": "Страйкбольное оборудование",
                "icon": "🛡️",
                "description": "Хронографы, зарядки, аккумуляторы",
                "count": equipment.count(),
                "url": "catalog_equipment",
                "color": "#0dcaf0",
            }
        )

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
            "title": "Страйкбольные игры",
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
            "title": "Аксессуары 3D печать",
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
            "title": "Страйкбольные привода",
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
            "title": "Аксессуары для приводов",
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
            "title": "Страйкбольное оборудование",
            "icon": "🛡️",
            "back_url": "catalog",
        },
    )


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

    if request.method == "POST":
        if user_registration:
            form = GameRegistrationEditForm(request.POST, instance=user_registration)
            if form.is_valid():
                form.save()
                messages.success(request, "✅ Статус успешно обновлен!")
                return redirect("game_detail", game_id=game.id)
        else:
            form = GameRegistrationForm(request.POST, user=request.user, game=game)
            if form.is_valid():
                registration = form.save(commit=False)
                registration.game = game
                if request.user.is_authenticated:
                    registration.user = request.user
                registration.save()
                messages.success(request, "✅ Вы успешно зарегистрировались на игру!")
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
    messages.success(request, "Вы отменили регистрацию на игру")
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
            messages.success(request, "Профиль успешно обновлен!")
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
        },
    )
