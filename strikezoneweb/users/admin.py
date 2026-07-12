from django.contrib import admin

from .models import User, Subscribers


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Настройки отображения User в админке."""
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name'
    )
    search_fields = (
        'username',
        'email',
    )


@admin.register(Subscribers)
class SubscribersAdmin(admin.ModelAdmin):
    """Настройки отображения Subscribers в админке."""
    list_display = (
        'user',
        'author',
    )
    search_fields = (
        'user__username',
        'author__username',
    )
