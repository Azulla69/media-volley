from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ModeratorPermission, StatisticianAssignment, Report


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'full_name', 'role', 'gender', 'city', 'is_active']
    list_filter = ['role', 'gender', 'city', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('middle_name', 'birth_date', 'phone', 'city', 'avatar', 'bio', 'height',
                       'vk_link', 'tg_link', 'tg_channel', 'max_link', 'gender', 'role')
        }),
    )


admin.site.register(User, CustomUserAdmin)


@admin.register(ModeratorPermission)
class ModeratorPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'championship', 'can_edit_teams', 'can_edit_matches', 'can_edit_players']
    list_filter = ['championship']


@admin.register(StatisticianAssignment)
class StatisticianAssignmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'match', 'assigned_at']
    list_filter = ['match__championship']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['reporter', 'reported', 'reason', 'created_at', 'is_resolved']
    list_filter = ['is_resolved']