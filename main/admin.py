from django.contrib import admin

from .models import (
    News,
    Tag,
    Favorite,
    Gun,
    Catalog,
    AirsoftGame,
    GunAccessory,
    GunModule,
    AirsoftEquipment,
    Profile,  # ← ДОБАВЛЯЕМ
    GameRegistration,  # ← ДОБАВЛЯЕМ (если есть)
)


admin.site.empty_value_display = 'Не задано'


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'is_published']
    list_filter = ['is_published', 'created_at', 'author']
    search_fields = ['title', 'content']
    date_hierarchy = 'created_at'
    list_editable = ['is_published']

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


class BaseAdmin(admin.ModelAdmin):
    """Общий интерфейс админ-панели блог."""

    list_editable = ('is_published',)
    list_display = ('id', 'title', 'is_published')
    list_display_links = ('id', 'title')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'slug'
    )
    search_fields = (
        'name',
        'slug',
    )


@admin.register(Gun)
class GunAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
    )
    search_fields = (
        'name',
    )


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_tags']
    list_filter = ['tags']
    search_fields = ['name', 'description']
    filter_horizontal = [
        'tags',
        'guns',
        'airsoft_equipment',
        'airsoft_games',
        'guns_accessories',
        'guns_modules'
    ]

    def get_tags(self, obj):
        """Метод должен быть внутри класса CatalogAdmin"""
        return ", ".join([tag.name for tag in obj.tags.all()])
    get_tags.short_description = 'Теги'


@admin.register(AirsoftGame)
class AirsoftGameAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'status', 'is_active', 'created_by']
    list_filter = ['status', 'is_active', 'date']
    search_fields = ['name', 'description', 'location']
    date_hierarchy = 'date'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user',
        'airsoft_gun',
    )
    search_fields = (
        'user__username',
        'user__email',
        'airsoft_gun__name',
    )


@admin.register(AirsoftEquipment)
class AirsoftEquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'in_stock']
    search_fields = ['name']


@admin.register(GunAccessory)
class GunAccessoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'in_stock']
    search_fields = ['name']


@admin.register(GunModule)
class GunModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'in_stock', 'material']
    search_fields = ['name']


# ===== ДОБАВЛЯЕМ РЕГИСТРАЦИЮ PROFILE =====

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'callsign', 'phone_number', 'birth_date']
    list_filter = ['role']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'callsign', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['role']
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Личная информация', {
            'fields': ('avatar', 'first_name', 'last_name', 'phone_number', 'birth_date', 'callsign')
        }),
        ('Права и роли', {
            'fields': ('role',)
        }),
        ('Дополнительно', {
            'fields': ('bio', 'created_at', 'updated_at')
        }),
    )


# ===== ДОБАВЛЯЕМ РЕГИСТРАЦИЮ GAME REGISTRATION =====

@admin.register(GameRegistration)
class GameRegistrationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'game', 'participation_status', 'has_car', 'registered_at']
    list_filter = ['participation_status', 'has_car', 'has_equipment']
    search_fields = ['first_name', 'last_name', 'phone_number', 'callsign', 'game__name']
    readonly_fields = ['registered_at', 'updated_at']
