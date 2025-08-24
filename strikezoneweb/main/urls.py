from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    path('catalog/', views.catalog, name='catalog'),
    path(
        'rules/', views.rules, name='rules'
    ),
    path(
        'profile',
        views.profile,
        name='profile',
    ),
]
