from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import Notification, Follow
from leagues.models import Championship


def home(request):
    championships = Championship.objects.filter(is_published=True)

    from matches.models import Match
    next_match = Match.objects.filter(
        status='SCHEDULED',
        date_time__gte=timezone.now(),
    ).select_related('team_home', 'team_away', 'championship').order_by('date_time').first()

    live_matches = Match.objects.filter(status='LIVE').select_related(
        'team_home', 'team_away', 'championship'
    ).prefetch_related('sets')[:3]

    recent_matches = Match.objects.filter(status='FINISHED').select_related(
        'team_home', 'team_away', 'championship'
    ).prefetch_related('sets').order_by('-date_time')[:5]

    from teams.models import Team
    from django.contrib.auth import get_user_model
    User = get_user_model()
    stats = {
        'championships': Championship.objects.filter(is_published=True).count(),
        'teams': Team.objects.count(),
        'players': User.objects.filter(role='PLAYER').count(),
        'matches': Match.objects.filter(status='FINISHED').count(),
    }

    return render(request, 'core/home.html', {
        'championships': championships,
        'next_match': next_match,
        'live_matches': live_matches,
        'recent_matches': recent_matches,
        'stats': stats,
    })


@login_required
def notifications_api(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    data = []
    for n in notifs:
        data.append({
            'id': n.id,
            'message': n.message,
            'link': n.link or '',
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
            'invite_id': n.invite.id if n.invite else None,
        })
    return JsonResponse(data, safe=False)


@login_required
def mark_read(request, notif_id):
    Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
def accept_invite(request, invite_id):
    from teams.models import TeamInvite, TeamPlayer, Team
    invite = get_object_or_404(TeamInvite, id=invite_id, player=request.user)

    if Team.objects.filter(players__player=request.user).count() >= 2:
        return JsonResponse({'ok': False, 'error': 'Вы уже состоите в 2 командах.'})

    if invite.is_main and invite.team.players.filter(is_main=True).count() >= 14:
        return JsonResponse({'ok': False, 'error': 'Основной состав заполнен.'})
    if not invite.is_main and invite.team.players.filter(is_main=False).count() >= 14:
        return JsonResponse({'ok': False, 'error': 'Запасной состав заполнен.'})

    invite.is_accepted = True
    invite.save()

    used_numbers = list(invite.team.players.values_list('jersey_number', flat=True))
    free_number = 1
    while free_number in used_numbers:
        free_number += 1

    TeamPlayer.objects.create(
        team=invite.team, player=request.user,
        jersey_number=free_number, position='SETTER',
        is_main=invite.is_main,
    )

    Notification.objects.create(
        user=invite.team.founder,
        message=f'{request.user.full_name} принял приглашение в «{invite.team.name}»',
    )
    Notification.objects.filter(user=request.user).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
def decline_invite(request, invite_id):
    from teams.models import TeamInvite
    invite = get_object_or_404(TeamInvite, id=invite_id, player=request.user)
    invite.is_accepted = False
    invite.save()
    Notification.objects.filter(user=request.user).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
def follow_player(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        return JsonResponse({'ok': False, 'error': 'Нельзя подписаться на себя'})
    follow, created = Follow.objects.get_or_create(follower=request.user, followed_user=target)
    if not created:
        follow.delete()
        return JsonResponse({'ok': True, 'action': 'unfollowed', 'count': target.followers.count()})
    return JsonResponse({'ok': True, 'action': 'followed', 'count': target.followers.count()})


@login_required
def follow_team(request, team_id):
    from teams.models import Team
    team = get_object_or_404(Team, id=team_id)
    follow, created = Follow.objects.get_or_create(follower=request.user, followed_team=team)
    if not created:
        follow.delete()
        return JsonResponse({'ok': True, 'action': 'unfollowed', 'count': team.followers.count()})
    return JsonResponse({'ok': True, 'action': 'followed', 'count': team.followers.count()})