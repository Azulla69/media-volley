from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from django.db.models import Q
from matches.models import Match
from leagues.models import Championship
from core.models import Notification
from core.utils import build_calendar_data
from .models import Team, TeamPlayer, TeamInvite
from django.contrib.auth import get_user_model
User = get_user_model()


def team_catalog(request):
    search = request.GET.get('q', '').strip()
    teams = Team.objects.select_related('captain', 'founder').prefetch_related('players')
    if search:
        teams = teams.filter(name__icontains=search)
    teams = teams.order_by('name')
    return render(request, 'teams/catalog.html', {'teams': teams, 'search': search})


@login_required
def my_teams(request):
    my_teams = Team.objects.filter(players__player=request.user).distinct()
    return render(request, 'teams/my_teams.html', {'my_teams': my_teams})


@login_required
def create_team(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Введите название команды.')
            return redirect('teams:my_teams')
        
        current_teams = Team.objects.filter(players__player=request.user).count()
        if current_teams >= 2:
            messages.error(request, 'Вы уже состоите в двух командах.')
            return redirect('teams:my_teams')
        
        team = Team.objects.create(name=name, founder=request.user)
        
        # Если основатель хочет быть в составе
        if request.POST.get('join_team') == 'on':
            if not team.captain:
                team.captain = request.user
                team.save()
            TeamPlayer.objects.create(
                team=team, player=request.user,
                jersey_number=request.POST.get('number', 1),
                position=request.POST.get('position', 'SETTER'),
            )
        
        messages.success(request, f'Команда «{team.name}» создана!')
        return redirect('teams:edit_team', team_id=team.id)
    return redirect('teams:my_teams')


@login_required
def edit_team(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    
    if team.founder != request.user:
        messages.error(request, 'Только основатель может редактировать команду.')
        return redirect('teams:my_teams')
    
    if request.method == 'POST':
        team.name = request.POST.get('name', team.name)
        if request.FILES.get('logo'):
            team.logo = request.FILES['logo']
        
        captain_id = request.POST.get('captain_id')
        if captain_id:
            new_captain = get_object_or_404(User, pk=captain_id)
            if team.players.filter(player=new_captain).exists():
                team.captain = new_captain
        
        team.save()
        
        for tp in team.players.all():
            prefix = f'player_{tp.player.id}'
            tp.jersey_number = request.POST.get(f'{prefix}_number', tp.jersey_number)
            tp.position = request.POST.get(f'{prefix}_position', tp.position)
            # Чекбокс: если отмечен — основной, иначе запасной
            tp.is_main = request.POST.get(f'{prefix}_is_main') == 'on'
            tp.save()
        
        messages.success(request, 'Команда обновлена!')
        return redirect('teams:edit_team', team_id=team.id)
    
    return render(request, 'teams/edit_team.html', {'team': team})


@login_required
def toggle_player_status(request, player_id):
    """Переключение игрока между основным и запасным составом"""
    tp = get_object_or_404(TeamPlayer, pk=player_id)
    team = tp.team
    
    if team.founder != request.user:
        messages.error(request, 'Нет доступа.')
        return redirect('teams:my_teams')
    
    if tp.is_main:
        # Переводим в запасные — без проверок
        tp.is_main = False
        tp.save()
    else:
        # Переводим в основной — проверяем лимит 14
        if team.players.filter(is_main=True).count() >= 14:
            messages.error(request, 'Основной состав не может превышать 14 человек.')
        else:
            tp.is_main = True
            tp.save()
    
    return redirect('teams:edit_team', team_id=team.id)
@login_required
def delete_team(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    
    if team.founder != request.user:
        messages.error(request, 'Только основатель может удалить команду.')
        return redirect('teams:my_teams')
    
    team.delete()
    messages.success(request, f'Команда «{team.name}» удалена.')
    return redirect('teams:my_teams')


@login_required
def invite_player(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if team.founder != request.user:
        messages.error(request, 'Только основатель может приглашать.')
        return redirect('teams:my_teams')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        is_main = request.POST.get('is_main') == 'on'
        player = get_object_or_404(User, pk=user_id)
        
        # Проверка лимитов
        if is_main and team.players.filter(is_main=True).count() >= 14:
            messages.error(request, 'Основной состав заполнен (макс. 14).')
            return redirect('teams:edit_team', team_id=team.id)
        if not is_main and team.players.filter(is_main=False).count() >= 14:
            messages.error(request, 'Запасной состав заполнен (макс. 14).')
            return redirect('teams:edit_team', team_id=team.id)
        if Team.objects.filter(players__player=player).count() >= 2:
            messages.error(request, f'{player.full_name} уже состоит в 2 командах.')
            return redirect('teams:edit_team', team_id=team.id)
        if TeamInvite.objects.filter(team=team, player=player).exists():
            messages.error(request, 'Приглашение уже отправлено.')
            return redirect('teams:edit_team', team_id=team.id)
        
        invite = TeamInvite.objects.create(team=team, player=player, is_main=is_main)
        Notification.objects.create(
            user=player,
            message=f'📨 Приглашение в команду «{team.name}» ({ "основной" if is_main else "запасной" } состав)',
            link='#',
            invite=invite,
        )
        messages.success(request, f'Приглашение отправлено {player.full_name}!')
        return redirect('teams:edit_team', team_id=team.id)
    
    users = User.objects.filter(role='PLAYER').exclude(id__in=team.players.values_list('player_id', flat=True))
    return render(request, 'teams/invite_player.html', {'team': team, 'users': users})


@login_required
def remove_player(request, team_id, player_id):
    team = get_object_or_404(Team, pk=team_id)
    if team.founder != request.user:
        messages.error(request, 'Нет доступа.')
        return redirect('teams:my_teams')
    
    TeamPlayer.objects.filter(team=team, player_id=player_id).delete()
    
    # Если удалили капитана — сбросить
    if team.captain and team.captain.id == player_id:
        team.captain = None
        team.save()
    
    messages.success(request, 'Игрок удалён из команды.')
    return redirect('teams:edit_team', team_id=team.id)
def team_detail(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    main_players = team.players.filter(is_main=True)
    bench_players = team.players.filter(is_main=False)

    team_matches = Match.objects.filter(
        Q(team_home=team) | Q(team_away=team)
    ).select_related('championship').prefetch_related('sets').order_by('-date_time')

    finished = [m for m in team_matches if m.status == 'FINISHED' and m.score_home is not None]
    total_games = len(finished)
    total_wins = sum(
        1 for m in finished
        if (m.team_home_id == team.id and m.score_home > m.score_away)
        or (m.team_away_id == team.id and m.score_away > m.score_home)
    )
    total_loses = total_games - total_wins

    today = date.today()
    team_match_dates = [
        m.date_time.date() for m in team_matches
        if m.date_time.year == today.year and m.date_time.month == today.month
    ]
    calendar_data = build_calendar_data(today.year, today.month, team_match_dates)

    championship_ids = team_matches.values_list('championship_id', flat=True).distinct()
    current_championships = Championship.objects.filter(id__in=championship_ids, is_active=True)

    from core.models import Follow
    is_following_team = request.user.is_authenticated and Follow.objects.filter(follower=request.user, followed_team=team).exists()
    team_followers_count = team.followers.count()
    return render(request, 'teams/team_detail.html', {
        'team': team,
        'main_players': main_players,
        'current_championships': current_championships,
        'bench_players': bench_players,
        'total_games': total_games,
        'total_wins': total_wins,
        'total_loses': total_loses,
        'calendar_data': calendar_data,
        'today': today,
        'matches': team_matches[:10],
        'is_following_team': is_following_team,
        'team_followers_count': team_followers_count,
    })