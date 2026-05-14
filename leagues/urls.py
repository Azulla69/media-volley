from django.urls import path
from . import views

app_name = 'leagues'

urlpatterns = [
    path('', views.championship_list, name='list'),
    path('<int:pk>/dashboard/', views.championship_dashboard, name='championship_dashboard'),
    path('<int:pk>/my-application/', views.my_application, name='my_application'),
    path('<int:pk>/', views.championship_detail, name='detail'),
    path('<int:pk>/apply/', views.apply_team, name='apply_team'),
    path('<int:pk>/export-pdf/', views.export_applications_pdf, name='export_pdf'),
]