from django.contrib import admin
from .models import Team, TeamPlayer


class TeamPlayerInline(admin.TabularInline):
    model = TeamPlayer
    extra = 1


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'captain', 'created_at']
    inlines = [TeamPlayerInline]