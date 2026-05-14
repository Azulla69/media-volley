from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Q, F, Count
from django.contrib.auth import get_user_model
from core.utils import calculate_championship_table

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
    from django.core.paginator import Paginator
    from leagues.models import Championship

    player = get_object_or_404(User, id=user_id)

    all_stats = player.match_stats.select_related(
        'match__championship', 'match__team_home', 'match__team_away'
    ).order_by('-match__date_time')

    total = all_stats.aggregate(
        total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
        attack=Sum('points_attack'), passes=Sum('passes'),
        block=Sum('points_block'), serve=Sum('points_serve'),
    )
    total_matches = all_stats.count()

    def type_stats(league_type):
        qs = all_stats.filter(match__championship__league_type=league_type)
        return qs.aggregate(
            total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
            attack=Sum('points_attack'), block=Sum('points_block'), serve=Sum('points_serve'),
            matches=Sum('id', filter=Q(id__gt=0)),
        ), qs.count()

    classic_stats, classic_count = type_stats('CLASSIC')
    beach_stats, beach_count = type_stats('BEACH')
    park_stats, park_count = type_stats('PARK')

    champ_ids = all_stats.values_list('match__championship_id', flat=True).distinct()
    champ_breakdown = []
    for champ in Championship.objects.filter(id__in=champ_ids):
        qs = all_stats.filter(match__championship=champ)
        agg = qs.aggregate(
            total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
            attack=Sum('points_attack'), passes=Sum('passes'),
            block=Sum('points_block'), serve=Sum('points_serve'),
        )
        champ_breakdown.append({
            'champ': champ,
            'matches': qs.count(),
            'total': agg['total'] or 0,
            'attack': agg['attack'] or 0,
            'passes': agg['passes'] or 0,
            'block': agg['block'] or 0,
            'serve': agg['serve'] or 0,
        })
    champ_breakdown.sort(key=lambda x: -x['total'])

    best_match = all_stats.annotate(
        pts=F('points_attack') + F('points_block') + F('points_serve')
    ).order_by('-pts').first()

    paginator = Paginator(all_stats, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'stats/player_stats.html', {
        'player': player,
        'total': total,
        'total_matches': total_matches,
        'classic_stats': classic_stats, 'classic_count': classic_count,
        'beach_stats': beach_stats, 'beach_count': beach_count,
        'park_stats': park_stats, 'park_count': park_count,
        'champ_breakdown': champ_breakdown,
        'best_match': best_match,
        'page_obj': page_obj,
    })


def team_rankings(request):
    from leagues.models import Championship, ChampionshipTeam

    championships = Championship.objects.filter(is_published=True).order_by('-id')
    selected_pk = request.GET.get('champ')

    if selected_pk:
        championships = championships.filter(pk=selected_pk)

    all_champs = Championship.objects.filter(is_published=True).order_by('-id')

    result = []
    for champ in championships:
        approved_teams = ChampionshipTeam.objects.filter(championship=champ, is_approved=True).select_related('team')
        finished = list(champ.matches.filter(status='FINISHED'))

        table = calculate_championship_table(approved_teams, finished)
        result.append({'champ': champ, 'table': table})

    return render(request, 'stats/team_rankings.html', {
        'result': result,
        'all_champs': all_champs,
        'selected_pk': selected_pk,
    })


def compare_players(request):
    p1_id = request.GET.get('p1')
    p2_id = request.GET.get('p2')
    player1 = player2 = None
    stats1 = stats2 = None
    champ_data1 = champ_data2 = []

    def get_player_data(player):
        all_stats = player.match_stats.select_related('match__championship')
        total = all_stats.aggregate(
            total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
            attack=Sum('points_attack'), passes=Sum('passes'),
            block=Sum('points_block'), serve=Sum('points_serve'),
        )
        matches = all_stats.count()
        best = all_stats.annotate(pts=F('points_attack') + F('points_block') + F('points_serve')).order_by('-pts').first()
        by_type = {}
        for lt in ['CLASSIC', 'BEACH', 'PARK']:
            qs = all_stats.filter(match__championship__league_type=lt)
            agg = qs.aggregate(
                total=Sum('points_attack') + Sum('points_block') + Sum('points_serve'),
            )
            by_type[lt] = {'matches': qs.count(), 'total': agg['total'] or 0}
        return {'total': total, 'matches': matches, 'best': best, 'by_type': by_type}

    all_players = User.objects.filter(role='PLAYER').order_by('last_name', 'first_name')

    if p1_id:
        player1 = get_object_or_404(User, id=p1_id)
        stats1 = get_player_data(player1)
    if p2_id:
        player2 = get_object_or_404(User, id=p2_id)
        stats2 = get_player_data(player2)

    return render(request, 'stats/compare.html', {
        'player1': player1, 'player2': player2,
        'stats1': stats1, 'stats2': stats2,
        'all_players': all_players,
        'p1_id': p1_id, 'p2_id': p2_id,
    })


def championship_stats(request, pk):
    from leagues.models import Championship

    champ = get_object_or_404(Championship, pk=pk)
    cf = Q(match_stats__match__championship=champ)

    top_scorers = (
        User.objects.filter(match_stats__match__championship=champ)
        .annotate(
            total=Sum('match_stats__points_attack', filter=cf)
                  + Sum('match_stats__points_block', filter=cf)
                  + Sum('match_stats__points_serve', filter=cf),
            attack=Sum('match_stats__points_attack', filter=cf),
            passes=Sum('match_stats__passes', filter=cf),
            block=Sum('match_stats__points_block', filter=cf),
            serve=Sum('match_stats__points_serve', filter=cf),
            matches_played=Sum('match_stats__id', filter=Q(match_stats__match__championship=champ) & Q(match_stats__id__gt=0)),
        )
        .filter(total__gt=0)
        .order_by('-total')
        .distinct()[:25]
    )

    matches_count = champ.matches.filter(status='FINISHED').count()

    return render(request, 'stats/championship_stats.html', {
        'champ': champ,
        'top_scorers': top_scorers,
        'matches_count': matches_count,
    })
