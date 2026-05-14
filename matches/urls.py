from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('<int:pk>/', views.match_detail, name='match_detail'),
    path('<int:pk>/manage/', views.match_manage, name='match_manage'),
    path('<int:pk>/live-update/', views.match_live_update, name='match_live_update'),
    path('<int:pk>/result/', views.match_manage, name='match_result'),
    path('referee/<int:pk>/accept/', views.accept_referee, name='accept_referee'),
    path('referee/<int:pk>/decline/', views.decline_referee, name='decline_referee'),
]
