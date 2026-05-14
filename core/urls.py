from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('core/notifications/', views.notifications_api, name='notifications'),
    path('core/notifications/read/<int:notif_id>/', views.mark_read, name='mark_read'),
    path('core/invites/accept/<int:invite_id>/', views.accept_invite, name='accept_invite'),
    path('core/invites/decline/<int:invite_id>/', views.decline_invite, name='decline_invite'),
    path('core/follow/player/<int:user_id>/', views.follow_player, name='follow_player'),
    path('core/follow/team/<int:team_id>/', views.follow_team, name='follow_team'),
]