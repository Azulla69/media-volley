from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Match, MatchSet, PlayerMatchStats, MatchReferee
from leagues.models import ChampionshipTeam
from users.models import ModeratorPermission, StatisticianAssignment


def _can_manage(user, match):
    if not user.is_authenticated:
        return False
    if user.role == 'ADMIN':
        return True
    if ModeratorPermission.objects.filter(user=user, championship=match.championship).exists():
        return True
    now = timezone.now()
    window = (match.date_time - timedelta(hours=24), match.date_time + timedelta(hours=24))
    if window[0] <= now <= window[1]:
        if MatchReferee.objects.filter(match=match, user=user, is_accepted=True).exists():
            return True
        if StatisticianAssignment.objects.filter(match=match, user=user).exists():
            return True
    return False


def match_detail(request, pk):
    match = get_object_or_404(Match, pk=pk)
    championship = match.championship

    sets = list(match.sets.all())

    home_app = ChampionshipTeam.objects.filter(championship=championship, team=match.team_home).first()
    away_app = ChampionshipTeam.objects.filter(championship=championship, team=match.team_away).first()
    home_players = list(home_app.players.select_related().all()) if home_app else []
    away_players = list(away_app.players.select_related().all()) if away_app else []

    stats_map = {s.player_id: s for s in PlayerMatchStats.objects.filter(match=match)}
    for player in home_players:
        player.match_stat = stats_map.get(player.id)
    for player in away_players:
        player.match_stat = stats_map.get(player.id)

    referees = MatchReferee.objects.filter(match=match, is_accepted=True).select_related('user')
    statisticians = StatisticianAssignment.objects.filter(match=match).select_related('user')

    can_manage = _can_manage(request.user, match)
    pending_ref = None
    if request.user.is_authenticated:
        pending_ref = MatchReferee.objects.filter(match=match, user=request.user, is_accepted__isnull=True).first()

    return render(request, 'matches/match_detail.html', {
        'match': match,
        'championship': championship,
        'sets': sets,
        'home_players': home_players,
        'away_players': away_players,
        'stats_map': stats_map,
        'has_stats': bool(stats_map),
        'referees': referees,
        'statisticians': statisticians,
        'can_manage': can_manage,
        'pending_ref': pending_ref,
    })


@login_required
def match_manage(request, pk):
    match = get_object_or_404(Match, pk=pk)
    championship = match.championship

    if not _can_manage(request.user, match):
        messages.error(request, 'Нет доступа.')
        return redirect('matches:match_detail', pk=pk)

    home_app = ChampionshipTeam.objects.filter(championship=championship, team=match.team_home).first()
    away_app = ChampionshipTeam.objects.filter(championship=championship, team=match.team_away).first()
    home_players = list(home_app.players.all()) if home_app else []
    away_players = list(away_app.players.all()) if away_app else []

    existing_sets = list(MatchSet.objects.filter(match=match).order_by('set_number'))
    existing_stats = {s.player_id: s for s in PlayerMatchStats.objects.filter(match=match)}

    if request.method == 'POST':
        action = request.POST.get('action', 'save_result')

        if action == 'save_result':
            MatchSet.objects.filter(match=match).delete()
            sets_home = sets_away = 0
            for i in range(1, 6):
                sh = request.POST.get(f'set_{i}_home', '').strip()
                sa = request.POST.get(f'set_{i}_away', '').strip()
                if sh == '' and sa == '':
                    continue
                if sh.isdigit() and sa.isdigit():
                    sh_i, sa_i = int(sh), int(sa)
                    MatchSet.objects.create(match=match, set_number=i, score_home=sh_i, score_away=sa_i)
                    if sh_i > sa_i:
                        sets_home += 1
                    else:
                        sets_away += 1
            match.score_home = sets_home
            match.score_away = sets_away
            match.status = 'FINISHED'
            match.save()
            _save_player_stats(request, match, home_players, away_players)
            messages.success(request, 'Результаты сохранены!')

        elif action == 'save_links':
            match.stream_link = request.POST.get('stream_link', '').strip()
            match.video_link = request.POST.get('video_link', '').strip()
            if request.FILES.get('protocol_file'):
                match.protocol_file = request.FILES['protocol_file']
            if request.FILES.get('protocol_photo'):
                match.protocol_photo = request.FILES['protocol_photo']
            match.save()
            messages.success(request, 'Ссылки и протокол сохранены.')

        elif action == 'set_live':
            match.status = 'LIVE'
            match.save()
            messages.success(request, 'Матч переведён в режим LIVE.')

        elif action == 'set_scheduled':
            match.status = 'SCHEDULED'
            match.score_home = None
            match.score_away = None
            match.save()
            messages.success(request, 'Статус сброшен.')

        elif action == 'save_nominations':
            mvp_home_id = request.POST.get('mvp_home')
            mvp_away_id = request.POST.get('mvp_away')
            match.mvp_home_id = mvp_home_id or None
            match.mvp_away_id = mvp_away_id or None
            match.save()
            messages.success(request, 'Номинации сохранены!')

        return redirect('matches:match_manage', pk=pk)

    sets_data = {s.set_number: s for s in existing_sets}
    sets_list = [sets_data.get(i) for i in range(1, 6)]
    for player in home_players:
        player.match_stat = existing_stats.get(player.id)
    for player in away_players:
        player.match_stat = existing_stats.get(player.id)

    return render(request, 'matches/match_manage.html', {
        'match': match,
        'championship': championship,
        'home_players': home_players,
        'away_players': away_players,
        'sets_list': sets_list,
    })


def _save_player_stats(request, match, home_players, away_players):
    all_players = home_players + away_players
    for player in all_players:
        if request.POST.get(f'attack_{player.id}') is None:
            continue
        stats, _ = PlayerMatchStats.objects.get_or_create(match=match, player_id=player.id)
        stats.points_attack = int(request.POST.get(f'attack_{player.id}') or 0)
        stats.passes = int(request.POST.get(f'passes_{player.id}') or 0)
        stats.points_block = int(request.POST.get(f'block_{player.id}') or 0)
        stats.points_serve = int(request.POST.get(f'serve_{player.id}') or 0)
        stats.save()


@login_required
def match_live_update(request, pk):
    """AJAX: обновление счёта в реальном времени."""
    match = get_object_or_404(Match, pk=pk)
    if not _can_manage(request.user, match):
        return JsonResponse({'ok': False, 'error': 'Нет доступа'}, status=403)

    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        set_num = int(data.get('set_num', 0))
        score_home = int(data.get('score_home', 0))
        score_away = int(data.get('score_away', 0))
        if set_num < 1 or set_num > 5:
            return JsonResponse({'ok': False, 'error': 'Неверный номер партии'})
        obj, _ = MatchSet.objects.update_or_create(
            match=match, set_number=set_num,
            defaults={'score_home': score_home, 'score_away': score_away}
        )
        sets = list(match.sets.all())
        sh = sum(1 for s in sets if s.score_home > s.score_away)
        sa = sum(1 for s in sets if s.score_away > s.score_home)
        match.score_home = sh
        match.score_away = sa
        match.save(update_fields=['score_home', 'score_away'])
        return JsonResponse({
            'ok': True,
            'score_home': sh, 'score_away': sa,
            'sets': [{'n': s.set_number, 'h': s.score_home, 'a': s.score_away} for s in sets],
        })
    return JsonResponse({'ok': False}, status=405)


@login_required
def accept_referee(request, pk):
    ref = get_object_or_404(MatchReferee, pk=pk, user=request.user)
    ref.is_accepted = True
    ref.save()
    from core.models import Notification
    Notification.objects.filter(user=request.user, link__contains=f'/matches/{ref.match_id}/').update(is_read=True)
    messages.success(request, 'Вы приняли назначение судьёй.')
    return redirect('matches:match_detail', pk=ref.match_id)


@login_required
def decline_referee(request, pk):
    ref = get_object_or_404(MatchReferee, pk=pk, user=request.user)
    ref.is_accepted = False
    ref.save()
    messages.info(request, 'Вы отказались от назначения.')
    return redirect('matches:match_detail', pk=ref.match_id)


