from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from matches.models import Match
from core.models import Notification
from leagues.models import ChampionshipTeam


class Command(BaseCommand):
    help = 'Отправляет уведомления игрокам за 12 часов до матча'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        window_start = now + timedelta(hours=11, minutes=30)
        window_end = now + timedelta(hours=12, minutes=30)

        matches = Match.objects.filter(
            status='SCHEDULED',
            date_time__gte=window_start,
            date_time__lte=window_end,
            reminder_sent=False,
        ).select_related('team_home', 'team_away', 'championship')

        count = 0
        for match in matches:
            dt_str = match.date_time.strftime('%d.%m.%Y в %H:%M')
            msg = (
                f'⏰ Через 12 часов матч: {match.team_home.name} vs {match.team_away.name} '
                f'— {dt_str}, {match.location}'
            )
            link = f'/matches/{match.pk}/'

            notified_ids = set()
            for app in ChampionshipTeam.objects.filter(
                championship=match.championship,
                team__in=[match.team_home, match.team_away],
                is_approved=True,
            ).prefetch_related('players'):
                for player in app.players.all():
                    if player.id not in notified_ids:
                        Notification.objects.create(user=player, message=msg, link=link)
                        notified_ids.add(player.id)
                        count += 1

            match.reminder_sent = True
            match.save(update_fields=['reminder_sent'])

        self.stdout.write(self.style.SUCCESS(f'Отправлено {count} уведомлений для {matches.count()} матчей'))
