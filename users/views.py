from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from .forms import CustomAuthenticationForm, ProfileEditForm, CustomUserCreationForm
from .models import Report, ModeratorPermission, StatisticianAssignment
from leagues.models import Championship
from teams.models import Team, TeamPlayer
from matches.models import Match, PlayerMatchStats
from datetime import date, timedelta
import calendar

User = get_user_model()


class CustomLogoutView(LogoutView):
    template_name = 'users/logout.html'
    next_page = 'core:home'


class CustomLogoutView(LogoutView):
    next_page = 'core:home'


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.role = 'PLAYER'
            user.save()
            
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            activation_link = request.build_absolute_uri(f'/users/activate/{uid}/{token}/')
            
            send_mail(
                'Подтверждение регистрации | Медиалига Волейбола',
                f'Здравствуйте, {user.first_name}!\n\n'
                f'Для активации аккаунта перейдите по ссылке:\n{activation_link}\n\n'
                f'Если вы не регистрировались, проигнорируйте это письмо.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            messages.success(request, 'На вашу почту отправлено письмо с подтверждением. Проверьте почту!')
            return redirect('users:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})


def activate_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Аккаунт подтверждён! Теперь вы можете войти.')
        return redirect('users:login')
    else:
        messages.error(request, 'Ссылка недействительна или устарела.')
        return redirect('core:home')


@login_required
def profile_view(request):
    player = request.user
    
    total_matches = player.match_stats.count()
    classic_matches = player.match_stats.filter(match__championship__league_type='CLASSIC').count()
    beach_matches = player.match_stats.filter(match__championship__league_type='BEACH').count()
    park_matches = player.match_stats.filter(match__championship__league_type='PARK').count()
    
    total_stats = player.match_stats.aggregate(
        total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
        attack=Sum('points_attack'), block=Sum('points_block'), serve=Sum('points_serve'),
    )
    classic_stats = player.match_stats.filter(match__championship__league_type='CLASSIC').aggregate(
        total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
        attack=Sum('points_attack'), block=Sum('points_block'), serve=Sum('points_serve'),
    )
    beach_stats = player.match_stats.filter(match__championship__league_type='BEACH').aggregate(
        total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
        attack=Sum('points_attack'), block=Sum('points_block'), serve=Sum('points_serve'),
    )
    park_stats = player.match_stats.filter(match__championship__league_type='PARK').aggregate(
        total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
        attack=Sum('points_attack'), block=Sum('points_block'), serve=Sum('points_serve'),
    )
    
    current_championships = player.team_memberships.filter(team__championship__is_active=True).select_related('team__championship')
    past_championships = player.team_memberships.filter(team__championship__is_active=False).select_related('team__championship')
    recent_matches = player.match_stats.select_related('match__championship', 'match__team_home', 'match__team_away').order_by('-match__date_time')[:10]
    
    hot_streak = 0
    for stat in player.match_stats.all().order_by('-match__date_time'):
        if stat.total_points > 0:
            hot_streak += 1
        else:
            break
    
    today = date.today()
    cal = calendar.monthcalendar(today.year, today.month)
    match_dates = list(player.match_stats.filter(match__date_time__year=today.year, match__date_time__month=today.month).dates('match__date_time', 'day'))
    calendar_data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day': '', 'has_match': False})
            else:
                week_data.append({'day': day, 'has_match': date(today.year, today.month, day) in match_dates})
        calendar_data.append(week_data)
    
    awards = []
    if total_matches >= 1:
        awards.append({'icon': '🌟', 'name': 'Дебютант', 'detail': 'Первый матч сыгран', 'championship': 'За всё время', 'year': '', 'color': 'bronze'})
    if total_matches >= 10:
        awards.append({'icon': '💯', 'name': 'Ветеран', 'detail': f'{total_matches} матчей', 'championship': 'За всё время', 'year': '', 'color': 'silver'})
    if total_matches >= 50:
        awards.append({'icon': '🦾', 'name': 'Железный человек', 'detail': f'{total_matches} матчей', 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    if total_matches >= 100:
        awards.append({'icon': '👑', 'name': 'Легенда', 'detail': f'{total_matches} матчей', 'championship': 'За всё время', 'year': '', 'color': 'diamond'})
    
    types_played = sum([1 for x in [classic_matches, beach_matches, park_matches] if x > 0])
    if classic_matches > 0:
        awards.append({'icon': '🏐', 'name': 'Классик', 'detail': f'{classic_matches} матчей', 'championship': 'Классический', 'year': '', 'color': 'silver'})
    if beach_matches > 0:
        awards.append({'icon': '🏖', 'name': 'Пляжник', 'detail': f'{beach_matches} матчей', 'championship': 'Пляжный', 'year': '', 'color': 'silver'})
    if park_matches > 0:
        awards.append({'icon': '🌳', 'name': 'Парковый', 'detail': f'{park_matches} матчей', 'championship': 'Парковый', 'year': '', 'color': 'silver'})
    if types_played >= 3:
        awards.append({'icon': '🏆', 'name': 'Король турниров', 'detail': 'Все три типа', 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    
    if player.captained_teams.exists():
        for ct in player.captained_teams.all():
            awards.append({'icon': '🎖', 'name': 'Капитан', 'detail': ct.name, 'championship': ct.championship.name, 'year': '', 'color': 'gold'})
    
    if total_stats.get('total') and total_stats['total'] >= 30:
        awards.append({'icon': '🔥', 'name': 'Бомбардир', 'detail': f"{total_stats['total']} очков", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    if total_stats.get('attack') and total_stats['attack'] >= 20:
        awards.append({'icon': '⚡', 'name': 'Атакующий', 'detail': f"{total_stats['attack']} ОЗ", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    if total_stats.get('block') and total_stats['block'] >= 10:
        awards.append({'icon': '🧱', 'name': 'Стена', 'detail': f"{total_stats['block']} ОБ", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    if total_stats.get('serve') and total_stats['serve'] >= 8:
        awards.append({'icon': '🎯', 'name': 'Эйс-машина', 'detail': f"{total_stats['serve']} ОП", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    
    awards.append({'icon': '🥇', 'name': 'Чемпион', 'detail': '1 место', 'championship': 'Ночная волейбольная лига', 'year': '2024', 'color': 'gold'})
    awards.append({'icon': '🥈', 'name': 'Чемпион', 'detail': '2 место', 'championship': 'Кубок Факела', 'year': '2023', 'color': 'silver'})
    awards.append({'icon': '🥉', 'name': 'Чемпион', 'detail': '3 место', 'championship': 'Рандом волейбол', 'year': '2024', 'color': 'bronze'})
    
    for cs, cn in [(classic_stats, 'Классический'), (beach_stats, 'Пляжный'), (park_stats, 'Парковый')]:
        if cs.get('total') and cs['total'] >= 20:
            awards.append({'icon': '🔥', 'name': 'Бомбардир', 'detail': f"{cs['total']} очков", 'championship': cn, 'year': '2024', 'color': 'gold'})
        if cs.get('attack') and cs['attack'] >= 15:
            awards.append({'icon': '⚡', 'name': 'Атакующий', 'detail': f"{cs['attack']} ОЗ", 'championship': cn, 'year': '2024', 'color': 'gold'})
        if cs.get('block') and cs['block'] >= 8:
            awards.append({'icon': '🧱', 'name': 'Стена', 'detail': f"{cs['block']} ОБ", 'championship': cn, 'year': '2024', 'color': 'gold'})
        if cs.get('serve') and cs['serve'] >= 5:
            awards.append({'icon': '🎯', 'name': 'Эйс-машина', 'detail': f"{cs['serve']} ОП", 'championship': cn, 'year': '2024', 'color': 'gold'})
    
    if total_matches >= 5:
        awards.append({'icon': '⭐', 'name': 'MVP турнира', 'detail': 'Лучший игрок', 'championship': 'Ночная волейбольная лига', 'year': '2024', 'color': 'diamond'})
    
    return render(request, 'users/profile.html', {
        'player': player, 'is_owner': True,
        'total_matches': total_matches, 'classic_matches': classic_matches, 'beach_matches': beach_matches, 'park_matches': park_matches,
        'total_stats': total_stats, 'classic_stats': classic_stats, 'beach_stats': beach_stats, 'park_stats': park_stats,
        'current_championships': current_championships, 'past_championships': past_championships,
        'recent_matches': recent_matches, 'awards': awards,
        'hot_streak': hot_streak, 'calendar_data': calendar_data, 'today': today,
    })


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён!')
            return redirect('users:profile')
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def report_user(request, user_id):
    if request.method == 'POST':
        reported_user = get_object_or_404(User, id=user_id)
        reason = request.POST.get('reason', '')
        if reason:
            Report.objects.create(reporter=request.user, reported=reported_user, reason=reason)
            messages.success(request, 'Жалоба отправлена. Администратор рассмотрит её.')
        else:
            messages.error(request, 'Укажите причину жалобы.')
    return redirect('users:profile')


# ========== АДМИН-ПАНЕЛЬ ==========

@login_required
def admin_panel(request):
    user = request.user
    
    # Проверка доступа
    if user.role == 'PLAYER':
        messages.error(request, 'У вас нет доступа к админ-панели.')
        return redirect('core:home')
    
    context = {'user': user}
    
    # Админ: всё
    if user.role == 'ADMIN':
        context['all_users'] = User.objects.all().order_by('-created_at')[:50]
        context['total_users'] = User.objects.count()
        context['reports'] = Report.objects.filter(is_resolved=False).order_by('-created_at')[:20]
        context['total_reports'] = Report.objects.filter(is_resolved=False).count()
        context['championships'] = Championship.objects.all()
        context['matches'] = Match.objects.all().order_by('-date_time')[:20]
        context['statisticians'] = StatisticianAssignment.objects.all().order_by('-assigned_at')[:20]
        context['moderators'] = ModeratorPermission.objects.all()
        context['recent_avatars'] = User.objects.exclude(avatar='').order_by('-updated_at')[:20]
    
    # Модератор: свои чемпионаты
    if user.role == 'MODERATOR':
        permissions = ModeratorPermission.objects.filter(user=user)
        context['permissions'] = permissions
        context['moderated_champs'] = [p.championship for p in permissions]
        context['moderated_matches'] = Match.objects.filter(championship__in=context['moderated_champs']).order_by('-date_time')[:20]
        context['moderated_teams'] = Team.objects.filter(championship__in=context['moderated_champs'])
    
    # Судья: просмотр матчей и протоколов
    if user.role == 'REFEREE':
        context['all_matches'] = Match.objects.all().order_by('-date_time')[:50]
        context['statistician_assignments'] = StatisticianAssignment.objects.all().order_by('-assigned_at')[:20]
    
    # Статист: свои матчи
    if user.role == 'STATISTICIAN':
        assignments = StatisticianAssignment.objects.filter(user=user)
        context['my_assignments'] = assignments
        context['active_assignments'] = []
        for a in assignments:
            if a.match.date_time + timedelta(hours=24) > timezone.now():
                context['active_assignments'].append(a)
    
    return render(request, 'users/admin_panel.html', context)


@login_required
def change_role(request, user_id):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Нет доступа.')
        return redirect('users:admin_panel')
    
    target = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(User.Role.choices):
            target.role = new_role
            target.save()
            messages.success(request, f'Роль {target.full_name} изменена на {target.get_role_display()}.')
    return redirect('users:admin_panel')


@login_required
def toggle_active(request, user_id):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Нет доступа.')
        return redirect('users:admin_panel')
    
    target = get_object_or_404(User, id=user_id)
    target.is_active = not target.is_active
    target.save()
    status = 'разблокирован' if target.is_active else 'заблокирован'
    messages.success(request, f'{target.full_name} {status}.')
    return redirect('users:admin_panel')


@login_required
def resolve_report(request, report_id):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Нет доступа.')
        return redirect('users:admin_panel')
    
    report = get_object_or_404(Report, id=report_id)
    report.is_resolved = True
    report.save()
    messages.success(request, 'Жалоба отмечена как решённая.')
    return redirect('users:admin_panel')


@login_required
def assign_moderator(request):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Нет доступа.')
        return redirect('users:admin_panel')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        champ_id = request.POST.get('champ_id')
        mod_user = get_object_or_404(User, id=user_id)
        champ = get_object_or_404(Championship, id=champ_id)
        
        # Даём роль модератора
        mod_user.role = 'MODERATOR'
        mod_user.save()
        
        # Создаём права
        ModeratorPermission.objects.get_or_create(
            user=mod_user, championship=champ,
            defaults={
                'can_edit_teams': request.POST.get('can_teams') == 'on',
                'can_edit_matches': request.POST.get('can_matches') == 'on',
                'can_edit_players': request.POST.get('can_players') == 'on',
                'can_edit_photos': request.POST.get('can_photos') == 'on',
            }
        )
        messages.success(request, f'{mod_user.full_name} назначен модератором {champ.name}.')
    return redirect('users:admin_panel')


@login_required
def assign_statistician(request):
    if request.user.role not in ['ADMIN', 'MODERATOR']:
        messages.error(request, 'Нет доступа.')
        return redirect('users:admin_panel')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        match_id = request.POST.get('match_id')
        stat_user = get_object_or_404(User, id=user_id)
        match = get_object_or_404(Match, id=match_id)
        
        stat_user.role = 'STATISTICIAN'
        stat_user.save()
        
        StatisticianAssignment.objects.get_or_create(user=stat_user, match=match)
        messages.success(request, f'{stat_user.full_name} назначен статистом на матч {match}.')
    return redirect('users:admin_panel')


@login_required
def remove_avatar(request, user_id):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Нет доступа.')
        return redirect('users:admin_panel')
    
    target = get_object_or_404(User, id=user_id)
    if target.avatar:
        target.avatar.delete()
        target.save()
        messages.success(request, f'Аватар пользователя {target.full_name} удалён.')
    return redirect('users:admin_panel')


from django.utils import timezone