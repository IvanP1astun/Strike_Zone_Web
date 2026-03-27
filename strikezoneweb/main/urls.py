from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<int:pk>/', views.catalog_detail, name='catalog_detail'),
    path(
        'rules/', views.rules, name='rules'
    ),
    path(
        'profile',
        views.profile,
        name='profile',
    ),
    path(
        'news/create/',
        views.NewsCreateView.as_view(),
        name='news_create'
    ),
]
