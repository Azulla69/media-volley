from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    path('activate/<uidb64>/<token>/', views.activate_view, name='activate'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('report/<int:user_id>/', views.report_user, name='report'),
    
    # Админ-панель
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/change-role/<int:user_id>/', views.change_role, name='change_role'),
    path('admin-panel/toggle-active/<int:user_id>/', views.toggle_active, name='toggle_active'),
    path('admin-panel/resolve-report/<int:report_id>/', views.resolve_report, name='resolve_report'),
    path('admin-panel/assign-moderator/', views.assign_moderator, name='assign_moderator'),
    path('admin-panel/assign-statistician/', views.assign_statistician, name='assign_statistician'),
    path('admin-panel/remove-avatar/<int:user_id>/', views.remove_avatar, name='remove_avatar'),
]