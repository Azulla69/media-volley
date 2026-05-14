from functools import wraps
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from .forms import CustomAuthenticationForm, ProfileEditForm, CustomUserCreationForm
from .models import Report, ModeratorPermission, StatisticianAssignment, Award, PlayerAward, SiteAward
from leagues.models import Championship
from teams.models import Team, TeamPlayer
from matches.models import Match, PlayerMatchStats, MatchReferee
from core.utils import build_calendar_data
from datetime import date, timedelta
import calendar

User = get_user_model()


def require_role(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, 'Нет доступа.')
                return redirect('users:admin_panel')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = CustomAuthenticationForm

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = User.objects.filter(username=username).first() or User.objects.filter(email=username).first()
        if user:
            user = authenticate(self.request, username=user.username, password=password)
        if user is not None:
            login(self.request, user)
            return redirect(self.get_success_url())
        form.add_error(None, 'Неверный логин/почта или пароль.')
        return self.form_invalid(form)


class CustomLogoutView(LogoutView):
    template_name = 'users/logout.html'
    next_page = 'core:home'


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.role = 'PLAYER'
            user.save()
            import os, random
            avatar_dir = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars')
            if os.path.exists(avatar_dir):
                avatars = [f for f in os.listdir(avatar_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.svg'))]
                if avatars:
                    from django.core.files import File
                    ra = random.choice(avatars)
                    user.avatar.save(ra, File(open(os.path.join(avatar_dir, ra), 'rb')), save=True)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            link = request.build_absolute_uri(f'/users/activate/{uid}/{token}/')
            send_mail(
                'Подтверждение регистрации | Медиалига Волейбола',
                f'Здравствуйте, {user.first_name}!\n\nСсылка для активации:\n{link}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            messages.success(request, 'Письмо отправлено!')
            return redirect('users:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})


def activate_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None
    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Аккаунт подтверждён!')
        return redirect('users:login')
    messages.error(request, 'Ссылка недействительна.')
    return redirect('core:home')


def _build_profile_context(player):
    from django.core.paginator import Paginator
    total_matches = player.match_stats.count()
    classic_matches = player.match_stats.filter(match__championship__league_type='CLASSIC').count()
    beach_matches = player.match_stats.filter(match__championship__league_type='BEACH').count()
    park_matches = player.match_stats.filter(match__championship__league_type='PARK').count()

    def _type_stats(league_type):
        return player.match_stats.filter(match__championship__league_type=league_type).aggregate(
            total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
            attack=Sum('points_attack'), passes=Sum('passes'),
            block=Sum('points_block'), serve=Sum('points_serve'),
        )

    total_stats = player.match_stats.aggregate(
        total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
        attack=Sum('points_attack'), passes=Sum('passes'),
        block=Sum('points_block'), serve=Sum('points_serve'),
    )

    hot_streak = 0
    for s in player.match_stats.all().order_by('-match__date_time'):
        if s.total_points > 0:
            hot_streak += 1
        else:
            break

    today = date.today()
    match_dates = list(
        player.match_stats.filter(
            match__date_time__year=today.year,
            match__date_time__month=today.month,
        ).dates('match__date_time', 'day')
    )
    calendar_data = build_calendar_data(today.year, today.month, match_dates)

    is_birthday = (
        player.birth_date
        and player.birth_date.month == today.month
        and player.birth_date.day == today.day
    )

    rating_position = None
    if total_stats.get('total') and total_stats['total'] > 0:
        all_pl = User.objects.filter(role='PLAYER')
        if player.gender:
            all_pl = all_pl.filter(gender=player.gender)
        all_pl = all_pl.annotate(
            total=Sum('match_stats__points_attack') + Sum('match_stats__points_block') + Sum('match_stats__points_serve')
        ).filter(total__gt=0).order_by('-total')
        for idx, p in enumerate(all_pl, 1):
            if p.id == player.id:
                rating_position = idx
                break

    awards = []
    for pa in PlayerAward.objects.filter(player=player).select_related('award__championship'):
        awards.append({
            'icon': pa.award.icon, 'name': pa.award.name, 'detail': pa.award.detail,
            'championship': pa.award.championship.name, 'year': pa.award.year, 'color': pa.award.color,
        })
    if total_matches >= 100:
        awards.append({'icon': '👑', 'name': 'Легенда', 'detail': f'{total_matches} матчей', 'championship': 'За всё время', 'year': '', 'color': 'diamond'})
    elif total_matches >= 50:
        awards.append({'icon': '🦾', 'name': 'Железный человек', 'detail': f'{total_matches} матчей', 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    elif total_matches >= 10:
        awards.append({'icon': '💯', 'name': 'Ветеран', 'detail': f'{total_matches} матчей', 'championship': 'За всё время', 'year': '', 'color': 'silver'})
    elif total_matches >= 1:
        awards.append({'icon': '🌟', 'name': 'Дебютант', 'detail': 'Первый матч', 'championship': 'За всё время', 'year': '', 'color': 'bronze'})

    all_stats_qs = player.match_stats.select_related(
        'match__championship', 'match__team_home', 'match__team_away'
    ).order_by('-match__date_time')
    years = list(
        player.match_stats.dates('match__date_time', 'year').values_list('match__date_time__year', flat=True)
    )

    return {
        'player': player,
        'total_matches': total_matches,
        'classic_matches': classic_matches,
        'beach_matches': beach_matches,
        'park_matches': park_matches,
        'total_stats': total_stats,
        'classic_stats': _type_stats('CLASSIC'),
        'beach_stats': _type_stats('BEACH'),
        'park_stats': _type_stats('PARK'),
        'site_awards': SiteAward.objects.filter(player=player),
        'current_championships': player.team_memberships.all().select_related('team'),
        'awards': awards,
        'hot_streak': hot_streak,
        'calendar_data': calendar_data,
        'today': today,
        'is_birthday': is_birthday,
        'rating_position': rating_position,
        'all_championships': Championship.objects.all(),
        'years': years,
        '_all_stats_qs': all_stats_qs,
    }


@login_required
def profile_view(request):
    player = request.user
    update_site_awards(player)
    ctx = _build_profile_context(player)
    all_stats_qs = ctx.pop('_all_stats_qs')
    total_stats = ctx['total_stats']
    total_matches = ctx['total_matches']
    classic_matches = ctx['classic_matches']
    beach_matches = ctx['beach_matches']
    park_matches = ctx['park_matches']

    classic_m = player.match_stats.filter(match__championship__league_type='CLASSIC').exists()
    beach_m = player.match_stats.filter(match__championship__league_type='BEACH').exists()
    park_m = player.match_stats.filter(match__championship__league_type='PARK').exists()
    types = sum(1 for x in [classic_m, beach_m, park_m] if x)
    if classic_m:
        ctx['awards'].append({'icon': '🏐', 'name': 'Классик', 'detail': f'{classic_matches} матчей', 'championship': 'Классический', 'year': '', 'color': 'silver'})
    if beach_m:
        ctx['awards'].append({'icon': '🏖', 'name': 'Пляжник', 'detail': f'{beach_matches} матчей', 'championship': 'Пляжный', 'year': '', 'color': 'silver'})
    if park_m:
        ctx['awards'].append({'icon': '🌳', 'name': 'Парковый', 'detail': f'{park_matches} матчей', 'championship': 'Парковый', 'year': '', 'color': 'silver'})
    if types >= 3:
        ctx['awards'].append({'icon': '🏆', 'name': 'Король турниров', 'detail': 'Все три типа', 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    for ct in player.captained_teams.all():
        ctx['awards'].append({'icon': '🎖', 'name': 'Капитан', 'detail': ct.name, 'championship': ct.name, 'year': '', 'color': 'gold'})
    if total_stats.get('total') and total_stats['total'] >= 30:
        ctx['awards'].append({'icon': '🔥', 'name': 'Бомбардир', 'detail': f"{total_stats['total']} очков", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    if total_stats.get('attack') and total_stats['attack'] >= 20:
        ctx['awards'].append({'icon': '⚡', 'name': 'Атакующий', 'detail': f"{total_stats['attack']} ОЗ", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    if total_stats.get('block') and total_stats['block'] >= 10:
        ctx['awards'].append({'icon': '🧱', 'name': 'Стена', 'detail': f"{total_stats['block']} ОБ", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    if total_stats.get('serve') and total_stats['serve'] >= 8:
        ctx['awards'].append({'icon': '🎯', 'name': 'Эйс-машина', 'detail': f"{total_stats['serve']} ОП", 'championship': 'За всё время', 'year': '', 'color': 'gold'})
    color_order = {'diamond': 0, 'gold': 1, 'silver': 2, 'bronze': 3}
    ctx['awards'].sort(key=lambda x: color_order.get(x['color'], 9))

    champ_search = request.GET.get('champ_search', '')
    type_f = request.GET.get('type', '')
    year_f = request.GET.get('year', '')
    if champ_search:
        all_stats_qs = all_stats_qs.filter(match__championship__name__icontains=champ_search)
    if type_f:
        all_stats_qs = all_stats_qs.filter(match__championship__league_type=type_f)
    if year_f:
        all_stats_qs = all_stats_qs.filter(match__date_time__year=year_f)
    from django.core.paginator import Paginator
    page_obj = Paginator(all_stats_qs, 20).get_page(request.GET.get('page', 1))

    ctx.update({
        'is_owner': True,
        'recent_matches': player.match_stats.select_related('match__championship', 'match__team_home', 'match__team_away').order_by('-match__date_time')[:3],
        'page_obj': page_obj,
        'filter_champ_search': champ_search,
        'filter_type': type_f,
        'filter_year': year_f,
    })
    return render(request, 'users/profile.html', ctx)


def public_profile_view(request, user_id):
    player = get_object_or_404(User, id=user_id)
    if request.user.is_authenticated and request.user.id == player.id:
        return redirect('users:profile')

    ctx = _build_profile_context(player)
    all_stats_qs = ctx.pop('_all_stats_qs')
    color_order = {'diamond': 0, 'gold': 1, 'silver': 2, 'bronze': 3}
    ctx['awards'].sort(key=lambda x: color_order.get(x['color'], 9))

    from django.core.paginator import Paginator
    page_obj = Paginator(all_stats_qs, 20).get_page(request.GET.get('page', 1))

    from core.models import Follow
    is_following = request.user.is_authenticated and Follow.objects.filter(follower=request.user, followed_user=player).exists()
    followers_count = player.followers.filter(followed_user=player).count()

    ctx.update({
        'is_owner': False,
        'recent_matches': player.match_stats.select_related('match__championship', 'match__team_home', 'match__team_away').order_by('-match__date_time')[:5],
        'page_obj': page_obj,
        'filter_champ_search': '',
        'filter_type': '',
        'filter_year': '',
        'is_following': is_following,
        'followers_count': followers_count,
    })
    return render(request, 'users/profile.html', ctx)


@login_required
def profile_edit(request):
    if request.method == 'POST':
        selected = request.POST.get('selected_avatar')
        if selected:
            import os
            path = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars', selected)
            if os.path.exists(path):
                from django.core.files import File
                request.user.avatar.save(selected, File(open(path, 'rb')), save=True)
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            if request.user.gender:
                user.gender = request.user.gender
            user.save()
            messages.success(request, 'Профиль обновлён!')
            return redirect('users:profile')
    else:
        form = ProfileEditForm(instance=request.user)
    import os
    avatar_dir = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars')
    avatar_list = sorted([
        f for f in os.listdir(avatar_dir)
        if f.endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp'))
    ]) if os.path.exists(avatar_dir) else []
    return render(request, 'users/profile_edit.html', {'form': form, 'avatar_list': avatar_list})


@login_required
def report_user(request, user_id):
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if reason:
            Report.objects.create(
                reporter=request.user,
                reported=get_object_or_404(User, id=user_id),
                reason=reason,
            )
            messages.success(request, 'Жалоба отправлена.')
        else:
            messages.error(request, 'Укажите причину.')
    return redirect('users:profile')


# ========== АДМИН-ПАНЕЛЬ ==========

@login_required
def admin_panel(request):
    user = request.user
    if user.role == 'PLAYER':
        messages.error(request, 'Нет доступа.')
        return redirect('core:home')
    context = {'user': user}

    if user.role == 'ADMIN':
        user_search = request.GET.get('user_search', '')
        all_users_qs = User.objects.all().order_by('-created_at')
        if user_search:
            from django.db.models import Q
            all_users_qs = all_users_qs.filter(
                Q(first_name__icontains=user_search) | Q(last_name__icontains=user_search) |
                Q(middle_name__icontains=user_search) | Q(username__icontains=user_search)
            )
        context['all_users_full'] = all_users_qs
        context['user_search'] = user_search
        from django.core.paginator import Paginator
        paginator = Paginator(all_users_qs, 10)
        context['users_page'] = paginator.get_page(request.GET.get('user_page', 1))
        context['all_championships_full'] = Championship.objects.all().order_by('-created_at')
        context['total_users'] = User.objects.count()
        context['reports'] = Report.objects.filter(is_resolved=False).order_by('-created_at')[:20]
        context['total_reports'] = Report.objects.filter(is_resolved=False).count()
        context['championships'] = Championship.objects.all()
        context['matches'] = Match.objects.all().order_by('-date_time')[:50]
        context['moderators'] = ModeratorPermission.objects.all()

    if user.role in ['ADMIN', 'MODERATOR']:
        if user.role == 'MODERATOR':
            perms = ModeratorPermission.objects.filter(user=user)
            context['moderated_champs'] = [p.championship for p in perms]
            champs_for_awards = context['moderated_champs']
        else:
            champs_for_awards = Championship.objects.all()
        context['moderated_awards'] = Award.objects.filter(championship__in=champs_for_awards).order_by('-created_at')
        context['all_players_for_awards'] = User.objects.filter(role='PLAYER')

    if user.role == 'REFEREE':
        context['all_matches'] = Match.objects.all().order_by('-date_time')[:50]

    if user.role == 'STATISTICIAN':
        assignments = StatisticianAssignment.objects.filter(user=user)
        context['my_assignments'] = assignments
        context['active_assignments'] = [
            a for a in assignments
            if a.match.date_time + timedelta(hours=24) > timezone.now()
        ]

    return render(request, 'users/admin_panel.html', context)


@login_required
@require_role('ADMIN')
def change_role(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(User.Role.choices):
            target.role = new_role
            target.save()
            messages.success(request, f'Роль {target.full_name} изменена.')
    return redirect('users:admin_panel')


@login_required
@require_role('ADMIN')
def toggle_active(request, user_id):
    target = get_object_or_404(User, id=user_id)
    target.is_active = not target.is_active
    target.save()
    messages.success(request, f'{target.full_name} {"разблокирован" if target.is_active else "заблокирован"}.')
    return redirect('users:admin_panel')


@login_required
@require_role('ADMIN')
def resolve_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.is_resolved = True
    report.save()
    messages.success(request, 'Жалоба решена.')
    return redirect('users:admin_panel')


@login_required
@require_role('ADMIN')
def assign_moderator(request):
    if request.method == 'POST':
        mod_user = get_object_or_404(User, id=request.POST.get('user_id'))
        champ = get_object_or_404(Championship, id=request.POST.get('champ_id'))
        mod_user.role = 'MODERATOR'
        mod_user.save()
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
@require_role('ADMIN', 'MODERATOR')
def assign_statistician(request):
    if request.method == 'POST':
        stat_user = get_object_or_404(User, id=request.POST.get('user_id'))
        match = get_object_or_404(Match, id=request.POST.get('match_id'))
        stat_user.role = 'STATISTICIAN'
        stat_user.save()
        StatisticianAssignment.objects.get_or_create(user=stat_user, match=match)
        messages.success(request, f'{stat_user.full_name} назначен статистом.')
    return redirect('users:admin_panel')


@login_required
@require_role('ADMIN')
def remove_avatar(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target.avatar:
        target.avatar.delete()
        target.save()
        messages.success(request, 'Аватар удалён.')
    return redirect('users:admin_panel')


@login_required
@require_role('ADMIN', 'MODERATOR')
def create_award(request):
    if request.method == 'POST':
        champ = get_object_or_404(Championship, id=request.POST.get('champ_id'))
        Award.objects.create(
            championship=champ,
            name=request.POST.get('name'),
            detail=request.POST.get('detail', ''),
            icon=request.POST.get('icon', '🏅'),
            color=request.POST.get('color', 'gold'),
            year=request.POST.get('year', ''),
            created_by=request.user,
        )
        messages.success(request, f'Награда "{request.POST.get("name")}" создана!')
    return redirect('users:admin_panel')


@login_required
@require_role('ADMIN', 'MODERATOR')
def assign_award(request):
    if request.method == 'POST':
        award = get_object_or_404(Award, id=request.POST.get('award_id'))
        player = get_object_or_404(User, id=request.POST.get('user_id'))
        _, created = PlayerAward.objects.get_or_create(player=player, award=award)
        if created:
            from core.models import Notification
            Notification.objects.create(
                user=player,
                message=f'🏅 Вам вручена награда «{award.name}» за турнир «{award.championship.name}»!',
                link='/users/awards/',
            )
        messages.success(request, f'{award.name} вручена {player.full_name}!')
    return redirect('users:admin_panel')


def awards_page(request):
    from leagues.models import Championship
    championships = Championship.objects.filter(
        awards__isnull=False
    ).prefetch_related('awards__players__player').distinct()
    champ_data = []
    for champ in championships:
        awards_qs = champ.awards.prefetch_related('players__player').all()
        if awards_qs.exists():
            champ_data.append({'champ': champ, 'awards': awards_qs})
    return render(request, 'users/awards_page.html', {
        'champ_data': champ_data,
        'is_admin': request.user.is_authenticated and request.user.role == 'ADMIN',
    })


@login_required
@require_role('ADMIN', 'MODERATOR')
def all_awards(request):
    awards = Award.objects.all().order_by('-created_at')
    if request.user.role == 'MODERATOR':
        perms = ModeratorPermission.objects.filter(user=request.user)
        champ_ids = [p.championship_id for p in perms]
        awards = awards.filter(championship_id__in=champ_ids)
    search = request.GET.get('search', '')
    if search:
        from django.db.models import Q
        awards = awards.filter(
            Q(name__icontains=search) | Q(championship__name__icontains=search) |
            Q(color__icontains=search) | Q(year__icontains=search)
        )
    from django.core.paginator import Paginator
    paginator = Paginator(awards, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'users/all_awards.html', {
        'awards': page_obj,
        'all_players': User.objects.filter(role='PLAYER'),
        'search': search,
    })


@login_required
@require_role('ADMIN', 'MODERATOR')
def edit_award(request, award_id):
    award = get_object_or_404(Award, id=award_id)
    if request.method == 'POST':
        award.name = request.POST.get('name', award.name)
        award.detail = request.POST.get('detail', award.detail)
        award.icon = request.POST.get('icon', award.icon)
        award.color = request.POST.get('color', award.color)
        award.year = request.POST.get('year', award.year)
        award.save()
        messages.success(request, 'Награда обновлена!')
    return redirect('users:all_awards')


@login_required
@require_role('ADMIN', 'MODERATOR')
def delete_award(request, award_id):
    award = get_object_or_404(Award, id=award_id)
    award.delete()
    messages.success(request, 'Награда удалена.')
    return redirect('users:all_awards')


@login_required
@require_role('ADMIN', 'MODERATOR')
def revoke_award(request, award_id, user_id):
    award = get_object_or_404(Award, id=award_id)
    player = get_object_or_404(User, id=user_id)
    PlayerAward.objects.filter(player=player, award=award).delete()
    messages.success(request, f'Награда отозвана у {player.full_name}.')
    return redirect('users:all_awards')


def update_site_awards(player):
    total_matches = player.match_stats.count()
    total_stats = player.match_stats.aggregate(
        total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
        attack=Sum('points_attack'),
        block=Sum('points_block'),
        serve=Sum('points_serve'),
    )
    max_in_match = player.match_stats.annotate(
        m=Sum('points_attack') + Sum('points_block') + Sum('points_serve')
    ).order_by('-m').first()
    max_points = max_in_match.total_points if max_in_match else 0
    classic = player.match_stats.filter(match__championship__league_type='CLASSIC').exists()
    beach = player.match_stats.filter(match__championship__league_type='BEACH').exists()
    park = player.match_stats.filter(match__championship__league_type='PARK').exists()
    captain_count = player.captained_teams.count()
    moderator_count = ModeratorPermission.objects.filter(user=player).count()
    statistician_count = StatisticianAssignment.objects.filter(user=player).count()
    referee_count = MatchReferee.objects.filter(user=player).count()
    awards_data = {
        'matches': (total_matches, 'matches'),
        'bombardier': (total_stats.get('total') or 0, 'stat'),
        'attacker': (total_stats.get('attack') or 0, 'stat'),
        'wall': (total_stats.get('block') or 0, 'stat'),
        'ace_machine': (total_stats.get('serve') or 0, 'stat'),
        'recordman': (max_points, 'stat'),
        'king': (sum([classic, beach, park]), 'types'),
        'captain': (captain_count, 'special'),
        'organizer': (moderator_count, 'special'),
        'statistician': (statistician_count, 'special'),
        'referee': (referee_count, 'special'),
    }
    rules = {
        'matches': [(1, 'bronze'), (5, 'silver'), (10, 'silver'), (50, 'gold'), (100, 'diamond'), (500, 'diamond')],
        'bombardier': [(50, 'bronze'), (250, 'silver'), (750, 'gold'), (1500, 'diamond')],
        'attacker': [(30, 'bronze'), (150, 'silver'), (500, 'gold'), (1000, 'diamond')],
        'wall': [(10, 'bronze'), (50, 'silver'), (200, 'gold'), (500, 'diamond')],
        'ace_machine': [(15, 'bronze'), (75, 'silver'), (250, 'gold'), (750, 'diamond')],
        'recordman': [(25, 'gold')],
        'king': [(3, 'gold')],
        'captain': [(1, 'bronze'), (5, 'silver'), (25, 'gold'), (100, 'diamond')],
        'organizer': [(1, 'bronze'), (5, 'silver'), (15, 'gold'), (50, 'diamond')],
        'statistician': [(1, 'bronze'), (25, 'silver'), (100, 'gold'), (350, 'diamond')],
        'referee': [(1, 'bronze'), (25, 'silver'), (100, 'gold'), (350, 'diamond')],
    }
    for award_type, (value, category) in awards_data.items():
        if value <= 0:
            continue
        level = None
        for threshold, lvl in rules.get(award_type, []):
            if value >= threshold:
                level = lvl
        if level:
            SiteAward.objects.update_or_create(
                player=player, award_type=award_type,
                defaults={'level': level, 'value': value}
            )
    if awards_data['king'][0] >= 3:
        SiteAward.objects.filter(player=player, award_type__in=['classic', 'beach', 'park']).delete()


@login_required
@require_role('ADMIN')
def create_championship(request):
    if request.method == 'POST':
        champ = Championship.objects.create(
            name=request.POST.get('name'),
            short_name=request.POST.get('short_name', ''),
            league_type=request.POST.get('league_type', 'CLASSIC'),
            stage=request.POST.get('stage', 'applications'),
            status=request.POST.get('status', 'active'),
            description=request.POST.get('description', ''),
            regulations=request.POST.get('regulations', ''),
            about_founders=request.POST.get('about_founders', ''),
            applications_deadline=request.POST.get('applications_deadline') or None,
            primary_color=request.POST.get('primary_color', '#1a73e8'),
            secondary_color=request.POST.get('secondary_color', '#ffffff'),
            telegram_link=request.POST.get('telegram_link', ''),
            vk_link=request.POST.get('vk_link', ''),
            max_link=request.POST.get('max_link', ''),
            is_published=False,
        )
        if request.FILES.get('logo'):
            champ.logo = request.FILES['logo']
            champ.save()
        from leagues.models import Founder
        founder_count = 1
        while True:
            first_name = request.POST.get(f'founder_first_name_{founder_count}')
            if not first_name:
                break
            Founder.objects.create(
                championship=champ,
                first_name=first_name,
                last_name=request.POST.get(f'founder_last_name_{founder_count}', ''),
                bio=request.POST.get(f'founder_bio_{founder_count}', ''),
                order=founder_count,
            )
            founder_count += 1

        award_count = 1
        while True:
            name = request.POST.get(f'award_name_{award_count}')
            if not name:
                break
            Award.objects.create(
                championship=champ,
                name=name,
                detail=request.POST.get(f'award_detail_{award_count}', ''),
                icon=request.POST.get(f'award_icon_{award_count}', '🏅'),
                color=request.POST.get(f'award_color_{award_count}', 'gold'),
                year=request.POST.get(f'award_year_{award_count}', ''),
                created_by=request.user,
            )
            award_count += 1
        messages.success(request, f'Чемпионат «{champ.name}» создан!')
        return redirect('leagues:detail', pk=champ.pk)
    return render(request, 'users/create_championship.html', {})


@login_required
@require_role('ADMIN')
def edit_championship(request, pk):
    champ = get_object_or_404(Championship, pk=pk)
    if request.method == 'POST':
        champ.name = request.POST.get('name', champ.name)
        champ.short_name = request.POST.get('short_name', '')
        champ.league_type = request.POST.get('league_type', champ.league_type)
        champ.stage = request.POST.get('stage', champ.stage)
        champ.description = request.POST.get('description', champ.description)
        champ.regulations = request.POST.get('regulations', '')
        champ.about_founders = request.POST.get('about_founders', '')
        champ.telegram_link = request.POST.get('telegram_link', '')
        champ.vk_link = request.POST.get('vk_link', '')
        champ.max_link = request.POST.get('max_link', '')
        champ.primary_color = request.POST.get('primary_color', champ.primary_color)
        champ.secondary_color = request.POST.get('secondary_color', champ.secondary_color)
        champ.is_published = 'is_published' in request.POST
        champ.is_active = 'is_active' in request.POST
        deadline = request.POST.get('applications_deadline', '').strip()
        champ.applications_deadline = deadline.replace('T', ' ') if deadline else None
        if request.FILES.get('logo'):
            champ.logo = request.FILES['logo']
        champ.save()
        messages.success(request, f'Чемпионат «{champ.name}» обновлён!')
        return redirect('users:edit_championship', pk=champ.pk)
    deadline_str = champ.applications_deadline.strftime('%Y-%m-%dT%H:%M') if champ.applications_deadline else ''
    return render(request, 'users/edit_championship.html', {
        'championship': champ,
        'deadline_str': deadline_str,
    })


@login_required
@require_role('ADMIN')
def publish_championship(request, pk):
    champ = get_object_or_404(Championship, pk=pk)
    champ.is_published = True
    champ.save()
    messages.success(request, f'Чемпионат «{champ.name}» опубликован!')
    return redirect('users:admin_panel')


@login_required
@require_role('ADMIN')
def add_founder(request, pk):
    from leagues.models import Founder
    from django.urls import reverse
    champ = get_object_or_404(Championship, pk=pk)
    if request.method == 'POST':
        Founder.objects.create(
            championship=champ,
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', ''),
            bio=request.POST.get('bio', ''),
            photo=request.FILES.get('photo'),
        )
        messages.success(request, 'Организатор добавлен!')
    return redirect(reverse('leagues:detail', args=[champ.pk]) + '?tab=organizer')


@login_required
@require_role('ADMIN')
def edit_founder(request, founder_id):
    from leagues.models import Founder
    from django.urls import reverse
    founder = get_object_or_404(Founder, id=founder_id)
    pk = founder.championship.pk
    if request.method == 'POST':
        founder.first_name = request.POST.get('first_name', founder.first_name)
        founder.last_name = request.POST.get('last_name', founder.last_name)
        founder.bio = request.POST.get('bio', founder.bio)
        if request.FILES.get('photo'):
            founder.photo = request.FILES['photo']
        founder.save()
        messages.success(request, 'Организатор обновлён!')
    return redirect(reverse('leagues:detail', args=[pk]) + '?tab=organizer')


@login_required
@require_role('ADMIN')
def delete_founder(request, founder_id):
    from leagues.models import Founder
    from django.urls import reverse
    founder = get_object_or_404(Founder, id=founder_id)
    pk = founder.championship.pk
    founder.delete()
    messages.success(request, 'Организатор удалён.')
    return redirect(reverse('leagues:detail', args=[pk]) + '?tab=organizer')


@login_required
@require_role('ADMIN')
def delete_championship(request, pk):
    champ = get_object_or_404(Championship, pk=pk)
    name = champ.name
    champ.delete()
    messages.success(request, f'Чемпионат «{name}» удалён.')
    return redirect('users:admin_panel')