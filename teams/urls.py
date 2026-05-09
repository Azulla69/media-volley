from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('my-teams/', views.my_teams, name='my_teams'),
    path('<int:team_id>/', views.team_detail, name='team_detail'),
    path('remove-player/<int:team_id>/<int:player_id>/', views.remove_player, name='remove_player'),
    path('toggle-player/<int:player_id>/', views.toggle_player_status, name='toggle_player'),
    path('delete/<int:team_id>/', views.delete_team, name='delete_team'),
    path('invite/<int:team_id>/', views.invite_player, name='invite_player'),
    path('create-team/', views.create_team, name='create_team'),
    path('edit/<int:team_id>/', views.edit_team, name='edit_team'),
]