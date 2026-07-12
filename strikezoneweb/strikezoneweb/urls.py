from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
]
