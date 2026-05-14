from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    path('activate/<uidb64>/<token>/', views.activate_view, name='activate'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<int:user_id>/', views.public_profile_view, name='public_profile'),
    path('report/<int:user_id>/', views.report_user, name='report'),
    
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/delete-championship/<int:pk>/', views.delete_championship, name='delete_championship'),
    path('admin-panel/create-championship/', views.create_championship, name='create_championship'),
    path('admin-panel/edit-championship/<int:pk>/', views.edit_championship, name='edit_championship'),
    path('admin-panel/publish-championship/<int:pk>/', views.publish_championship, name='publish_championship'),
    path('admin-panel/add-founder/<int:pk>/', views.add_founder, name='add_founder'),
    path('admin-panel/edit-founder/<int:founder_id>/', views.edit_founder, name='edit_founder'),
    path('admin-panel/delete-founder/<int:founder_id>/', views.delete_founder, name='delete_founder'),
    path('admin-panel/revoke-award/<int:award_id>/<int:user_id>/', views.revoke_award, name='revoke_award'),
    path('admin-panel/delete-award/<int:award_id>/', views.delete_award, name='delete_award'),
    path('admin-panel/edit-award/<int:award_id>/', views.edit_award, name='edit_award'),
    path('admin-panel/change-role/<int:user_id>/', views.change_role, name='change_role'),
    path('admin-panel/toggle-active/<int:user_id>/', views.toggle_active, name='toggle_active'),
    path('admin-panel/resolve-report/<int:report_id>/', views.resolve_report, name='resolve_report'),
    path('admin-panel/assign-moderator/', views.assign_moderator, name='assign_moderator'),
    path('admin-panel/assign-statistician/', views.assign_statistician, name='assign_statistician'),
    path('admin-panel/remove-avatar/<int:user_id>/', views.remove_avatar, name='remove_avatar'),
    path('admin-panel/create-award/', views.create_award, name='create_award'),
    path('awards/', views.awards_page, name='awards_page'),
    path('admin-panel/all-awards/', views.all_awards, name='all_awards'),
    path('admin-panel/assign-award/', views.assign_award, name='assign_award'),
    
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset.html',
        email_template_name='users/password_reset_email.html',
        subject_template_name='users/password_reset_subject.txt',
        success_url='/users/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url='/users/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),
]