from django.urls import path
from . import views

app_name = 'stats'

urlpatterns = [
    path('leaders/', views.leaders_board, name='leaders'),
    path('player/<int:user_id>/', views.player_stats, name='player_stats'),
    path('teams/', views.team_rankings, name='team_rankings'),
    path('championship/<int:pk>/', views.championship_stats, name='championship_stats'),
    path('compare/', views.compare_players, name='compare'),
]
