from django.urls import path
from . import views

app_name = 'leagues'

urlpatterns = [
    path('', views.championship_list, name='list'),
    path('<int:pk>/', views.championship_detail, name='detail'),
]