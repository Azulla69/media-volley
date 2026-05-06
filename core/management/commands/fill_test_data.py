from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User, ModeratorPermission
from leagues.models import Championship
from teams.models import Team, TeamPlayer
from matches.models import Match, PlayerMatchStats
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Заполняет базу расширенными тестовыми данными'

    def handle(self, *args, **kwargs):
        # Суперпользователь
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@volley.ru', 'admin123',
                                         first_name='Админ', last_name='Главный', role='ADMIN')
            self.stdout.write('Создан admin / admin123')

        # Чемпионаты
        champs = []
        for name, short, lt, color, desc in [
            ('Ночная волейбольная лига Хабаровска', 'НВЛ', 'CLASSIC', '#1a73e8', 'Ночная лига для любителей.'),
            ('Рандом волейбол', 'РВ', 'CLASSIC', '#e83a1a', 'Случайные составы.'),
            ('Кубок Факела', 'КФ', 'PARK', '#f4a100', 'Парковый кубок.'),
            ('Кубок Губернатора', 'КГ', 'BEACH', '#009688', 'Пляжный турнир.'),
            ('Волейбол на песке', 'ВП', 'BEACH', '#00bcd4', 'Летний пляжный чемпионат.'),
            ('Парковая лига', 'ПЛ', 'PARK', '#7c4dff', 'Весенне-осенний парковый.'),
        ]:
            c, _ = Championship.objects.get_or_create(name=name, short_name=short, league_type=lt,
                                                       defaults={'description': desc, 'primary_color': color})
            champs.append(c)

        # Игроки
        players_data = [
            ('ivanov', 'Алексей', 'Иванов', 'Петрович', 'M'),
            ('petrov', 'Сергей', 'Петров', 'Александрович', 'M'),
            ('smirnov', 'Дмитрий', 'Смирнов', 'Игоревич', 'M'),
            ('kuznetsov', 'Артём', 'Кузнецов', 'Сергеевич', 'M'),
            ('popov', 'Максим', 'Попов', 'Дмитриевич', 'M'),
            ('sokolov', 'Евгений', 'Соколов', 'Владимирович', 'M'),
            ('volkov', 'Никита', 'Волков', 'Андреевич', 'M'),
            ('morozov', 'Илья', 'Морозов', 'Алексеевич', 'M'),
            ('ivanova', 'Анна', 'Иванова', 'Сергеевна', 'F'),
            ('petrova', 'Мария', 'Петрова', 'Алексеевна', 'F'),
            ('smirnova', 'Елена', 'Смирнова', 'Дмитриевна', 'F'),
            ('kuznetsova', 'Ольга', 'Кузнецова', 'Игоревна', 'F'),
        ]
        players = []
        for uname, first, last, middle, gender in players_data:
            user, _ = User.objects.get_or_create(username=uname, defaults={
                'first_name': first, 'last_name': last, 'middle_name': middle,
                'gender': gender, 'role': 'PLAYER', 'email': f'{uname}@volley.ru',
                'bio': f'Привет! Я {first}, играю в волейбол с детства.',
            })
            user.set_password('player123')
            user.save()
            players.append(user)

        # Модератор и судья
        mod, _ = User.objects.get_or_create(username='moderator', defaults={'first_name': 'Модер', 'last_name': 'Модераторов', 'role': 'MODERATOR'})
        mod.set_password('moder123'); mod.save()
        ref, _ = User.objects.get_or_create(username='referee', defaults={'first_name': 'Судья', 'last_name': 'Судейский', 'role': 'REFEREE'})
        ref.set_password('ref123'); ref.save()
        ModeratorPermission.objects.get_or_create(user=mod, championship=champs[0])

        # Команды — по 2 на чемпионат
        team_names = ['Зенит', 'Локомотив', 'Динамо', 'Спартак', 'Авангард', 'Факел',
                      'Торнадо', 'Молния', 'Вихрь', 'Атлант', 'Буревестник', 'Тигры']
        teams = []
        for i, tname in enumerate(team_names):
            t, _ = Team.objects.get_or_create(championship=champs[i // 2], name=tname,
                                               defaults={'captain': players[i % len(players)]})
            teams.append(t)

        # Игроки в команды
        positions = ['SETTER', 'OUTSIDE_HITTER', 'OPPOSITE', 'LIBERO', 'MIDDLE_BLOCKER']
        for i, p in enumerate(players):
            for j in range(2):
                TeamPlayer.objects.get_or_create(
                    team=teams[(i * 2 + j) % len(teams)], player=p,
                    defaults={'jersey_number': i + 1, 'position': positions[i % 5]}
                )

        for t in teams:
            if t.players.exists():
                t.captain = t.players.first().player
                t.save()

        # Удаляем старые матчи и статистику перед созданием новых
        PlayerMatchStats.objects.all().delete()
        Match.objects.all().delete()

        # Матчи и статистика
        now = timezone.now()
        for champ in champs:
            champ_teams = list(Team.objects.filter(championship=champ))
            if len(champ_teams) < 2:
                continue
            for week in range(8):
                pairs = [(0, 1)] if len(champ_teams) < 4 else [(0, 1), (2, 3)]
                for h, a in pairs:
                    if h >= len(champ_teams) or a >= len(champ_teams):
                        continue
                    sh = random.choice([3, 2, 1, 0])
                    sa = random.choice([0, 1, 2, 3])
                    match = Match.objects.create(
                        championship=champ, team_home=champ_teams[h], team_away=champ_teams[a],
                        date_time=now - timedelta(days=random.randint(1, 180)),
                        location=random.choice(['Спорткомплекс "Олимпиец"', 'Пляжный корт', 'Парк "Динамо"', 'Стадион "Юность"']),
                        status='FINISHED', score_home=sh, score_away=sa,
                    )
                    is_home_win = sh > sa
                    for team, is_winner in [(champ_teams[h], is_home_win), (champ_teams[a], not is_home_win)]:
                        for tp in team.players.all():
                            base = random.randint(8, 20) if is_winner else random.randint(2, 10)
                            PlayerMatchStats.objects.get_or_create(
                                match=match, player=tp.player,
                                defaults={
                                    'points_attack': base + random.randint(0, 10),
                                    'points_block': random.randint(0, 6) + (3 if is_winner else 0),
                                    'points_serve': random.randint(0, 5) + (2 if is_winner else 0),
                                    'aces': random.randint(0, 4),
                                    'blocks': random.randint(0, 5),
                                    'errors': random.randint(0, 6),
                                }
                            )

        self.stdout.write('Готово! admin/admin123, ivanov/player123')