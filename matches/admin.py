from django.contrib import admin
from .models import Match, PlayerMatchStats


class PlayerMatchStatsInline(admin.TabularInline):
    model = PlayerMatchStats
    extra = 1


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'championship', 'status', 'date_time', 'score_home', 'score_away']
    list_filter = ['championship', 'status']
    inlines = [PlayerMatchStatsInline]