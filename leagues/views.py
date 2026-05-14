from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import F
from .models import Championship, ChampionshipPhoto, ChampionshipTeam, Founder
from teams.models import Team, TeamPlayer
from matches.models import Match, MatchReferee
from users.models import Award, PlayerAward, ModeratorPermission, StatisticianAssignment
from core.utils import calculate_championship_table


def championship_list(request):
    championships = Championship.objects.filter(is_published=True)
    return render(request, 'leagues/list.html', {'championships': championships})


def championship_detail(request, pk):
    championship = get_object_or_404(Championship, pk=pk)
    teams = []
    matches = Match.objects.filter(championship=championship).prefetch_related('sets').order_by('date_time')
    photos = ChampionshipPhoto.objects.filter(championship=championship).order_by('order')
    awards = Award.objects.filter(championship=championship)
    founders = Founder.objects.filter(championship=championship).order_by('order')
    applications = ChampionshipTeam.objects.filter(championship=championship)
    approved_teams = applications.filter(is_approved=True)

    finished = [m for m in matches if m.status == 'FINISHED' and m.score_home is not None]
    table = calculate_championship_table(approved_teams, finished)
    
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
        'founders': founders,
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
def _dashboard_handle_stage(request, championship, action):
    from core.models import Notification
    stage_transitions = {
        'end_applications': ('applications', 'review', 'Приём заявок завершён.'),
        'reopen_applications': ('review', 'applications', 'Приём заявок снова открыт.'),
        'pause_championship': ('active', 'review', 'Чемпионат возвращён на этап приёма заявок.'),
        'finish_championship': ('active', 'finished', '🏆 Чемпионат завершён!'),
        'reopen_championship': ('finished', 'active', 'Чемпионат снова активен.'),
    }
    if action in stage_transitions:
        from_stage, to_stage, msg = stage_transitions[action]
        if championship.stage == from_stage:
            championship.stage = to_stage
            championship.save()
            messages.success(request, msg)
    elif action == 'start_championship':
        if championship.stage == 'review' and ChampionshipTeam.objects.filter(championship=championship, is_approved=True).count() >= 2:
            championship.stage = 'active'
            championship.save()
            messages.success(request, '🏐 Чемпионат начался!')


def _dashboard_handle_application(request, championship, action):
    from core.models import Notification
    app_id = request.POST.get('app_id')
    app = get_object_or_404(ChampionshipTeam, pk=app_id)
    if action == 'approve':
        app.is_approved = True
        app.save()
        for recipient in {app.team.captain, app.team.founder}:
            if recipient:
                Notification.objects.create(
                    user=recipient,
                    message=f'✅ Заявка команды «{app.team.name}» на чемпионат «{championship.name}» одобрена!',
                    link=f'/leagues/{championship.pk}/',
                )
        messages.success(request, f'Заявка «{app.team.name}» одобрена!')
    elif action == 'reject':
        for recipient in {app.team.captain, app.team.founder}:
            if recipient:
                Notification.objects.create(
                    user=recipient,
                    message=f'❌ Заявка команды «{app.team.name}» на чемпионат «{championship.name}» отклонена.',
                    link=f'/leagues/{championship.pk}/',
                )
        app.delete()
        messages.success(request, 'Заявка отклонена.')


def _dashboard_handle_match(request, championship, action):
    if action == 'create_match':
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
        match = get_object_or_404(Match, pk=request.POST.get('match_id'))
        match.team_home_id = request.POST.get('team_home')
        match.team_away_id = request.POST.get('team_away')
        match.date_time = request.POST.get('date_time').replace('T', ' ')
        match.location = request.POST.get('location', match.location)
        match.save()
        messages.success(request, 'Матч обновлён.')
    elif action == 'update_score':
        match = get_object_or_404(Match, pk=request.POST.get('match_id'))
        match.score_home = request.POST.get('score_home')
        match.score_away = request.POST.get('score_away')
        match.status = 'FINISHED'
        match.save()
        messages.success(request, 'Счёт обновлён!')
    elif action == 'delete_match':
        Match.objects.filter(pk=request.POST.get('match_id')).delete()
        messages.success(request, 'Матч удалён.')


def _dashboard_handle_assignment(request, championship, action):
    from core.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if action == 'assign_referee':
        match = get_object_or_404(Match, pk=request.POST.get('match_id'), championship=championship)
        user = get_object_or_404(User, pk=request.POST.get('user_id'))
        ref, created = MatchReferee.objects.get_or_create(match=match, user=user)
        if created:
            Notification.objects.create(
                user=user,
                message=f'⚖️ Вас назначили судьёй на матч {match.team_home} vs {match.team_away} ({match.date_time:%d.%m.%Y %H:%M})',
                link=f'/matches/{match.pk}/',
            )
            messages.success(request, f'{user.full_name} назначен(а) судьёй.')
        else:
            messages.info(request, 'Этот судья уже назначен.')
    elif action == 'remove_referee':
        MatchReferee.objects.filter(pk=request.POST.get('ref_id'), match__championship=championship).delete()
        messages.success(request, 'Судья снят с матча.')
    elif action == 'assign_statistician':
        match = get_object_or_404(Match, pk=request.POST.get('match_id'), championship=championship)
        user = get_object_or_404(User, pk=request.POST.get('user_id'))
        _, created = StatisticianAssignment.objects.get_or_create(match=match, user=user)
        if created:
            Notification.objects.create(
                user=user,
                message=f'📊 Вас назначили статистом на матч {match.team_home} vs {match.team_away} ({match.date_time:%d.%m.%Y %H:%M})',
                link=f'/matches/{match.pk}/',
            )
            messages.success(request, f'{user.full_name} назначен(а) статистом.')
        else:
            messages.info(request, 'Этот статист уже назначен.')
    elif action == 'remove_statistician':
        StatisticianAssignment.objects.filter(pk=request.POST.get('st_id'), match__championship=championship).delete()
        messages.success(request, 'Статист снят с матча.')
    elif action == 'add_moderator':
        user = get_object_or_404(User, pk=request.POST.get('user_id'))
        _, created = ModeratorPermission.objects.get_or_create(user=user, championship=championship)
        if created:
            messages.success(request, f'{user.full_name} добавлен(а) как модератор.')
        else:
            messages.info(request, 'Уже является модератором.')
    elif action == 'remove_moderator':
        ModeratorPermission.objects.filter(pk=request.POST.get('mod_id'), championship=championship).delete()
        messages.success(request, 'Модератор удалён.')


def _dashboard_generate_schedule(request, championship):
    from datetime import datetime, timedelta
    approved_teams = [app.team for app in ChampionshipTeam.objects.filter(championship=championship, is_approved=True)]
    if len(approved_teams) < 2:
        messages.error(request, 'Нужно минимум 2 одобренных команды.')
        return
    base_date = request.POST.get('base_date', '').strip()
    if not base_date:
        messages.error(request, 'Укажите начальную дату.')
        return
    try:
        current_dt = datetime.strptime(base_date, '%Y-%m-%dT%H:%M')
    except ValueError:
        messages.error(request, 'Неверный формат даты.')
        return
    slot_hours = max(1, int(request.POST.get('slot_hours') or 2))
    location = request.POST.get('location', 'Спорткомплекс')
    double_round = request.POST.get('double_round') == 'on'
    n = len(approved_teams)
    rotation_teams = approved_teams[:]
    if n % 2 == 1:
        rotation_teams.append(None)
        n += 1
    fixed = rotation_teams[0]
    rotation = rotation_teams[1:]
    pairs = []
    for _ in range(n - 1):
        circle = [fixed] + rotation
        for i in range(n // 2):
            t1, t2 = circle[i], circle[n - 1 - i]
            if t1 is not None and t2 is not None:
                pairs.append((t1, t2))
        rotation = [rotation[-1]] + rotation[:-1]
    if double_round:
        pairs += [(t2, t1) for t1, t2 in pairs]
    for t1, t2 in pairs:
        Match.objects.create(
            championship=championship, team_home=t1, team_away=t2,
            date_time=current_dt, location=location, status='SCHEDULED',
        )
        current_dt += timedelta(hours=slot_hours)
    messages.success(request, f'Сгенерировано {len(pairs)} матчей!')


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
        stage_actions = {'end_applications', 'reopen_applications', 'start_championship',
                         'finish_championship', 'pause_championship', 'reopen_championship'}
        app_actions = {'approve', 'reject'}
        match_actions = {'create_match', 'update_match', 'update_score', 'delete_match'}
        assign_actions = {'assign_referee', 'remove_referee', 'assign_statistician',
                          'remove_statistician', 'add_moderator', 'remove_moderator'}

        if action in stage_actions:
            _dashboard_handle_stage(request, championship, action)
        elif action in app_actions:
            _dashboard_handle_application(request, championship, action)
        elif action in match_actions:
            _dashboard_handle_match(request, championship, action)
        elif action in assign_actions:
            _dashboard_handle_assignment(request, championship, action)
        elif action == 'generate_schedule':
            _dashboard_generate_schedule(request, championship)

        return redirect('leagues:championship_dashboard', pk=championship.pk)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    referees_users = User.objects.filter(role='REFEREE').order_by('last_name', 'first_name')
    statisticians_users = User.objects.filter(role='STATISTICIAN').order_by('last_name', 'first_name')
    champ_moderators = ModeratorPermission.objects.filter(championship=championship).select_related('user')

    for m in matches:
        m.refs = MatchReferee.objects.filter(match=m).select_related('user')
        m.stats = StatisticianAssignment.objects.filter(match=m).select_related('user')

    return render(request, 'leagues/championship_dashboard.html', {
        'championship': championship,
        'applications': applications,
        'approved_teams': approved_teams,
        'matches': matches,
        'referees_users': referees_users,
        'statisticians_users': statisticians_users,
        'champ_moderators': champ_moderators,
    })


@login_required
def export_applications_pdf(request, pk):
    from django.http import HttpResponse
    championship = get_object_or_404(Championship, pk=pk)
    user = request.user
    is_mod = ModeratorPermission.objects.filter(user=user, championship=championship).exists()
    if user.role != 'ADMIN' and not is_mod:
        from django.contrib import messages
        messages.error(request, 'Нет доступа.')
        return redirect('leagues:championship_dashboard', pk=pk)

    applications = ChampionshipTeam.objects.filter(
        championship=championship
    ).select_related('team__captain', 'team__founder').prefetch_related('players')

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=16, spaceAfter=6, fontName='Helvetica-Bold')
        sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=10, spaceAfter=12, textColor=colors.grey)
        h2_style = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=12, spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold')
        body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=9)

        story.append(Paragraph(championship.name, title_style))
        story.append(Paragraph(f'Экспорт заявок | {championship.get_league_type_display()} | Этап: {championship.get_stage_display()}', sub_style))
        story.append(Spacer(1, 0.3*cm))

        for app in applications:
            status = 'ОДОБРЕНА' if app.is_approved else 'НА РАССМОТРЕНИИ'
            story.append(Paragraph(f'{app.team.name}   [{status}]', h2_style))

            captain = app.team.captain
            cap_phone = captain.phone if captain else '—'
            cap_vk = captain.vk_link if captain else '—'
            cap_tg = captain.tg_link if captain else '—'
            story.append(Paragraph(f'Капитан: {captain.full_name if captain else "—"}   Тел: {cap_phone}   VK: {cap_vk}   TG: {cap_tg}', body_style))
            story.append(Spacer(1, 0.2*cm))

            players = list(app.players.all())
            data = [['#', 'ФИО', 'Пол', 'Город', 'Телефон']]
            for i, p in enumerate(players, 1):
                data.append([
                    str(i),
                    p.full_name,
                    p.get_gender_display() if p.gender else '—',
                    p.city or '—',
                    p.phone or '—',
                ])

            if len(data) > 1:
                col_widths = [0.8*cm, 5.5*cm, 2.2*cm, 3*cm, 3.5*cm]
                t = Table(data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a73e8')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
                    ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
                    ('ALIGN', (0,0), (0,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ]))
                story.append(t)
            else:
                story.append(Paragraph('Игроки не добавлены', body_style))
            story.append(Spacer(1, 0.5*cm))

        doc.build(story)
        buf.seek(0)
        filename = f'applications_{championship.pk}.pdf'
        response = HttpResponse(buf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ImportError:
        from django.contrib import messages
        messages.error(request, 'Для PDF-экспорта установите reportlab: pip install reportlab')
        return redirect('leagues:championship_dashboard', pk=pk)

