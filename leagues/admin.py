from django.contrib import admin
from .models import Championship, ChampionshipPhoto


class ChampionshipPhotoInline(admin.TabularInline):
    model = ChampionshipPhoto
    extra = 1


@admin.register(Championship)
class ChampionshipAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'league_type', 'is_active']
    list_filter = ['league_type', 'is_active']
    inlines = [ChampionshipPhotoInline]