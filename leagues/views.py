from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import F
from .models import Championship, ChampionshipPhoto, ChampionshipTeam
from teams.models import Team, TeamPlayer
from matches.models import Match
from users.models import Award, PlayerAward


def championship_list(request):
    championships = Championship.objects.filter(is_published=True)
    return render(request, 'leagues/list.html', {'championships': championships})


def championship_detail(request, pk):
    championship = get_object_or_404(Championship, pk=pk)
    teams = []
    matches = Match.objects.filter(championship=championship).order_by('date_time')
    photos = ChampionshipPhoto.objects.filter(championship=championship).order_by('order')
    awards = Award.objects.filter(championship=championship)
    applications = ChampionshipTeam.objects.filter(championship=championship)
    approved_teams = applications.filter(is_approved=True)
    
    table = []
    for app in approved_teams:
        team = app.team
        played = matches.filter(team_home=team).count() + matches.filter(team_away=team).count()
        won = matches.filter(team_home=team, score_home__gt=F('score_away')).count() + matches.filter(team_away=team, score_away__gt=F('score_home')).count()
        lost = played - won
        table.append({'team': team, 'played': played, 'won': won, 'lost': lost, 'points': won * 3})
    table.sort(key=lambda x: (-x['points'], -x['won']))
    
    tab = request.GET.get('tab', 'about')
    
    deadline_passed = False
    if championship.applications_deadline and championship.applications_deadline < timezone.now():
        if championship.stage == 'applications':
            championship.stage = 'review'
            championship.save()
        deadline_passed = True
    
    user_application = None
    if request.user.is_authenticated:
        user_application = ChampionshipTeam.objects.filter(
            championship=championship,
            team__players__player=request.user,
            team__players__is_main=True,
        ).first()
    
    return render(request, 'leagues/detail.html', {
        'championship': championship,
        'teams': teams,
        'matches': matches,
        'photos': photos,
        'awards': awards,
        'applications': applications,
        'approved_teams': approved_teams,
        'table': table,
        'tab': tab,
        'deadline_passed': deadline_passed,
        'user_application': user_application,
        'now': timezone.now(),
    })


@login_required
def apply_team(request, pk):
    championship = get_object_or_404(Championship, pk=pk)
    if championship.stage != 'applications':
        messages.error(request, 'Сейчас не принимаются заявки.')
        return redirect('leagues:detail', pk=championship.pk)
    
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        player_ids = request.POST.getlist('players')
        team = get_object_or_404(Team, pk=team_id)
        
        if request.user != team.founder and request.user != team.captain:
            messages.error(request, 'Только основатель или капитан может подать заявку.')
            return redirect('leagues:detail', pk=championship.pk)
        
        if len(player_ids) < 6:
            messages.error(request, 'Минимум 6 игроков в заявке.')
            return redirect('leagues:apply_team', pk=championship.pk)
        if len(player_ids) > 14:
            messages.error(request, 'Максимум 14 игроков в заявке.')
            return redirect('leagues:apply_team', pk=championship.pk)
        
        if ChampionshipTeam.objects.filter(championship=championship, team=team).exists():
            messages.error(request, 'Заявка от этой команды уже подана.')
        else:
            app = ChampionshipTeam.objects.create(championship=championship, team=team)
            app.players.set(player_ids)
            
            # Уведомления модераторам чемпионата
            from core.models import Notification
            from users.models import ModeratorPermission
            moderators = ModeratorPermission.objects.filter(championship=championship)
            for mod_perm in moderators:
                Notification.objects.create(
                    user=mod_perm.user,
                    message=f'📨 Новая заявка от команды «{team.name}» на чемпионат «{championship.name}»',
                    link=f'/leagues/{championship.pk}/manage-applications/',
                )
            
            messages.success(request, f'Заявка от команды «{team.name}» подана! ({len(player_ids)} игроков)')
        return redirect('leagues:detail', pk=championship.pk)
    
    user_teams = Team.objects.filter(
        players__player=request.user
    ).distinct()
    
    return render(request, 'leagues/apply_team.html', {
        'championship': championship,
        'user_teams': user_teams,
    })



@login_required
def my_application(request, pk):
    championship = get_object_or_404(Championship, pk=pk)
    application = get_object_or_404(ChampionshipTeam, championship=championship, team__players__player=request.user)
    team = application.team
    
    # Проверка: только основатель или капитан
    if request.user != team.founder and request.user != team.captain:
        messages.error(request, 'Нет доступа к заявке.')
        return redirect('leagues:detail', pk=championship.pk)
    
    if request.method == 'POST':
        player_ids = request.POST.getlist('players')
        if len(player_ids) < 6:
            messages.error(request, 'Минимум 6 игроков.')
        elif len(player_ids) > 14:
            messages.error(request, 'Максимум 14 игроков.')
        else:
            application.players.set(player_ids)
            messages.success(request, 'Заявка обновлена!')
        return redirect('leagues:my_application', pk=championship.pk)
    
    selected_ids = list(application.players.values_list('id', flat=True))
    
    return render(request, 'leagues/my_application.html', {
        'application': application,
        'team': team,
        'championship': championship,
        'selected_ids': selected_ids,
    })
@login_required
def championship_dashboard(request, pk):
    championship = get_object_or_404(Championship, pk=pk)
    if request.user.role not in ['ADMIN', 'MODERATOR']:
        messages.error(request, 'Нет доступа.')
        return redirect('leagues:detail', pk=championship.pk)
    
    applications = ChampionshipTeam.objects.filter(championship=championship).select_related('team__captain', 'team__founder')
    approved_teams = applications.filter(is_approved=True)
    matches = Match.objects.filter(championship=championship).order_by('date_time')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'end_applications':
            if championship.stage == 'applications':
                championship.stage = 'review'
                championship.save()
                messages.success(request, 'Приём заявок завершён.')
        
        elif action == 'reopen_applications':
            if championship.stage == 'review':
                championship.stage = 'applications'
                championship.save()
                messages.success(request, 'Приём заявок снова открыт.')
        
        elif action == 'approve':
            app_id = request.POST.get('app_id')
            app = get_object_or_404(ChampionshipTeam, pk=app_id)
            app.is_approved = True
            app.save()
            messages.success(request, f'Заявка «{app.team.name}» одобрена!')
        
        elif action == 'reject':
            app_id = request.POST.get('app_id')
            ChampionshipTeam.objects.filter(pk=app_id).delete()
            messages.success(request, 'Заявка отклонена.')
        
        elif action == 'create_match':
            Match.objects.create(
                championship=championship,
                team_home_id=request.POST.get('team_home'),
                team_away_id=request.POST.get('team_away'),
                date_time=request.POST.get('date_time').replace('T', ' '),
                location=request.POST.get('location', 'Спорткомплекс'),
                status='SCHEDULED',
            )
            messages.success(request, 'Матч добавлен.')
        
        elif action == 'update_match':
            match_id = request.POST.get('match_id')
            match = get_object_or_404(Match, pk=match_id)
            match.team_home_id = request.POST.get('team_home')
            match.team_away_id = request.POST.get('team_away')
            match.date_time = request.POST.get('date_time').replace('T', ' ')
            match.location = request.POST.get('location', match.location)
            match.save()
            messages.success(request, 'Матч обновлён.')
        
        elif action == 'update_score':
            match_id = request.POST.get('match_id')
            match = get_object_or_404(Match, pk=match_id)
            match.score_home = request.POST.get('score_home')
            match.score_away = request.POST.get('score_away')
            match.status = 'FINISHED'
            match.save()
            messages.success(request, 'Счёт обновлён!')
        
        elif action == 'delete_match':
            match_id = request.POST.get('match_id')
            Match.objects.filter(pk=match_id).delete()
            messages.success(request, 'Матч удалён.')
        
        elif action == 'start_championship':
            if championship.stage == 'review' and approved_teams.count() >= 2:
                championship.stage = 'active'
                championship.save()
                messages.success(request, '🏐 Чемпионат начался!')
        
        elif action == 'finish_championship':
            if championship.stage == 'active':
                championship.stage = 'finished'
                championship.save()
                messages.success(request, '🏆 Чемпионат завершён!')
        elif action == 'pause_championship':
            if championship.stage == 'active':
                championship.stage = 'review'
                championship.save()
                messages.success(request, 'Чемпионат возвращён на этап приёма заявок.')
        
        elif action == 'reopen_championship':
            if championship.stage == 'finished':
                championship.stage = 'active'
                championship.save()
                messages.success(request, 'Чемпионат снова активен.')
        
        return redirect('leagues:championship_dashboard', pk=championship.pk)
    
    return render(request, 'leagues/championship_dashboard.html', {
        'championship': championship,
        'applications': applications,
        'approved_teams': approved_teams,
        'matches': matches,
    })

