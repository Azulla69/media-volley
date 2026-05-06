from django.shortcuts import render
from django.db.models import Sum, Q, F
from django.contrib.auth import get_user_model

User = get_user_model()


def leaders_board(request):
    sort_by = request.GET.get('sort', 'total_points')
    gender_filter = request.GET.get('gender', 'all')
    league_type = request.GET.get('type', 'all')
    
    players = User.objects.filter(role='PLAYER')
    
    if gender_filter != 'all':
        players = players.filter(gender=gender_filter)
    
    stats_filter = Q()
    if league_type != 'all':
        stats_filter = Q(match__championship__league_type=league_type)
    
    players = players.annotate(
        total_attack=Sum('match_stats__points_attack', filter=stats_filter),
        total_block=Sum('match_stats__points_block', filter=stats_filter),
        total_serve=Sum('match_stats__points_serve', filter=stats_filter),
    ).annotate(
        total_points=F('total_attack') + F('total_block') + F('total_serve')
    ).order_by(f'-{sort_by}')
    
    players = [p for p in players if p.total_points and p.total_points > 0]
    
    return render(request, 'stats/leaders.html', {
        'players': players,
        'current_sort': sort_by,
        'current_gender': gender_filter,
        'current_type': league_type,
    })


def player_stats(request, user_id):
    player = User.objects.get(id=user_id, role='PLAYER')
    
    classic_stats = player.match_stats.filter(match__championship__league_type='CLASSIC').aggregate(
        OZ=Sum('points_attack'), OB=Sum('points_block'), OP=Sum('points_serve')
    )
    beach_stats = player.match_stats.filter(match__championship__league_type='BEACH').aggregate(
        OZ=Sum('points_attack'), OB=Sum('points_block'), OP=Sum('points_serve')
    )
    
    recent_matches = player.match_stats.all().order_by('-match__date_time')[:10]
    
    return render(request, 'stats/player_stats.html', {
        'player': player,
        'classic_stats': classic_stats,
        'beach_stats': beach_stats,
        'recent_matches': recent_matches,
    })