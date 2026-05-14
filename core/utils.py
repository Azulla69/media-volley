import calendar as _calendar
from datetime import date
from django.db.models import Sum


def calculate_championship_table(approved_teams, finished_matches):
    table = []
    for app in approved_teams:
        team = app.team
        played = won = lost = sets_won = sets_lost = points = 0
        for m in finished_matches:
            if m.team_home_id == team.id:
                sw, sl = m.score_home or 0, m.score_away or 0
            elif m.team_away_id == team.id:
                sw, sl = m.score_away or 0, m.score_home or 0
            else:
                continue
            played += 1
            sets_won += sw
            sets_lost += sl
            if sw > sl:
                won += 1
                points += 2 if sl == 2 else 3
            else:
                lost += 1
                points += 1 if sw == 2 else 0
        table.append({
            'team': team, 'played': played, 'won': won, 'lost': lost,
            'sets_won': sets_won, 'sets_lost': sets_lost,
            'sets_ratio': f'{sets_won}:{sets_lost}' if played else '—',
            'points': points,
        })
    table.sort(key=lambda x: (-x['points'], -x['won'], -(x['sets_won'] - x['sets_lost'])))
    return table


def build_calendar_data(year, month, event_dates=()):
    cal = _calendar.monthcalendar(year, month)
    event_set = set(event_dates)
    result = []
    for week in cal:
        result.append([
            {
                'day': day if day else '',
                'has_match': date(year, month, day) in event_set if day else False,
            }
            for day in week
        ])
    return result
