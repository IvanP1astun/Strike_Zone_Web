from django.urls import path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    # ===== АВТОРИЗАЦИЯ =====
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    # ===== КАТАЛОГ =====
    path("catalog/", views.catalog, name="catalog"),
    path("catalog/<int:pk>/", views.catalog_detail, name="catalog_detail"),
    # Разделы каталога
    path("catalog/games/", views.catalog_games, name="catalog_games"),
    path("catalog/games/<int:game_id>/", views.game_detail, name="game_detail"),
    path(
        "catalog/games/cancel/<int:registration_id>/",
        views.cancel_registration,
        name="cancel_registration",
    ),
    path("catalog/modules/", views.catalog_modules, name="catalog_modules"),
    path("catalog/guns/", views.catalog_guns, name="catalog_guns"),
    path("catalog/accessories/", views.catalog_accessories, name="catalog_accessories"),
    path("catalog/equipment/", views.catalog_equipment, name="catalog_equipment"),
    path("rules/", views.rules, name="rules"),
    path("news/create/", views.NewsCreateView.as_view(), name="news_create"),
]
