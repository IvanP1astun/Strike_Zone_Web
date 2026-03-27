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
    list_display = ['name']
    search_fields = ['name']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'airsoft_gun',
    )
    search_fields = (
        'user__username',
        'user__email',
        'airsoft_gun__name',
    )


@admin.register(AirsoftEquipment)
class AirsoftEquipmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(GunAccessory)
class GunAccessoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(GunModule)
class GunModuleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
