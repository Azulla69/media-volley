from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User, ModeratorPermission
from leagues.models import Championship, ChampionshipPhoto
from teams.models import Team, TeamPlayer
from matches.models import Match, PlayerMatchStats
from datetime import timedelta


class Command(BaseCommand):
    help = 'Заполняет базу тестовыми данными'

    def handle(self, *args, **kwargs):
        # Создаём суперпользователя, если нет
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@volley.ru', 'admin123',
                                         first_name='Админ', last_name='Главный', role='ADMIN')
            self.stdout.write('Создан суперпользователь: admin / admin123')

        # Создаём чемпионаты
        champ1, _ = Championship.objects.get_or_create(
            name='Ночная волейбольная лига Хабаровска',
            defaults={
                'short_name': 'НВЛ',
                'league_type': 'CLASSIC',
                'description': 'Ночная лига для любителей волейбола. Игры проходят по вечерам в будние дни.',
                'about_founders': 'Основана в 2020 году группой энтузиастов.',
                'telegram_link': 'https://t.me/nvl_khv',
                'vk_link': 'https://vk.com/nvl_khv',
                'primary_color': '#1a73e8',
                'secondary_color': '#ffffff',
            }
        )

        champ2, _ = Championship.objects.get_or_create(
            name='Рандом волейбол',
            defaults={
                'short_name': 'РВ',
                'league_type': 'CLASSIC',
                'description': 'Турнир со случайными командами. Составы определяются жеребьёвкой перед каждым туром.',
                'about_founders': 'Создан для того, чтобы игроки могли играть в разных составах.',
                'telegram_link': 'https://t.me/random_volley',
                'primary_color': '#e83a1a',
                'secondary_color': '#ffffff',
            }
        )

        champ3, _ = Championship.objects.get_or_create(
            name='Кубок Факела',
            defaults={
                'short_name': 'КФ',
                'league_type': 'CLASSIC',
                'description': 'Ежегодный кубок среди сильнейших команд города.',
                'about_founders': 'Проводится при поддержке федерации волейбола.',
                'vk_link': 'https://vk.com/kubok_fakela',
                'primary_color': '#f4a100',
                'secondary_color': '#000000',
            }
        )

        champ4, _ = Championship.objects.get_or_create(
            name='Кубок Губернатора',
            defaults={
                'short_name': 'КГ',
                'league_type': 'BEACH',
                'description': 'Престижный турнир по пляжному волейболу на песке.',
                'about_founders': 'Проводится под патронажем губернатора края.',
                'telegram_link': 'https://t.me/kubok_gubernatora',
                'primary_color': '#009688',
                'secondary_color': '#ffffff',
            }
        )

        self.stdout.write('Созданы 4 чемпионата')

        # Создаём игроков
        players_data = [
            {'username': 'ivanov', 'first': 'Алексей', 'last': 'Иванов', 'middle': 'Петрович', 'gender': 'M'},
            {'username': 'petrov', 'first': 'Сергей', 'last': 'Петров', 'middle': 'Александрович', 'gender': 'M'},
            {'username': 'smirnov', 'first': 'Дмитрий', 'last': 'Смирнов', 'middle': 'Игоревич', 'gender': 'M'},
            {'username': 'kuznetsov', 'first': 'Артём', 'last': 'Кузнецов', 'middle': 'Сергеевич', 'gender': 'M'},
            {'username': 'popov', 'first': 'Максим', 'last': 'Попов', 'middle': 'Дмитриевич', 'gender': 'M'},
            {'username': 'sokolov', 'first': 'Евгений', 'last': 'Соколов', 'middle': 'Владимирович', 'gender': 'M'},
            {'username': 'volkov', 'first': 'Никита', 'last': 'Волков', 'middle': 'Андреевич', 'gender': 'M'},
            {'username': 'morozov', 'first': 'Илья', 'last': 'Морозов', 'middle': 'Алексеевич', 'gender': 'M'},
            {'username': 'ivanova', 'first': 'Анна', 'last': 'Иванова', 'middle': 'Сергеевна', 'gender': 'F'},
            {'username': 'petrova', 'first': 'Мария', 'last': 'Петрова', 'middle': 'Алексеевна', 'gender': 'F'},
            {'username': 'smirnova', 'first': 'Елена', 'last': 'Смирнова', 'middle': 'Дмитриевна', 'gender': 'F'},
            {'username': 'kuznetsova', 'first': 'Ольга', 'last': 'Кузнецова', 'middle': 'Игоревна', 'gender': 'F'},
            {'username': 'popova', 'first': 'Татьяна', 'last': 'Попова', 'middle': 'Владимировна', 'gender': 'F'},
            {'username': 'sokolova', 'first': 'Дарья', 'last': 'Соколова', 'middle': 'Андреевна', 'gender': 'F'},
            {'username': 'volkova', 'first': 'Ксения', 'last': 'Волкова', 'middle': 'Евгеньевна', 'gender': 'F'},
            {'username': 'morozova', 'first': 'Анастасия', 'last': 'Морозова', 'middle': 'Павловна', 'gender': 'F'},
        ]

        players = []
        for pdata in players_data:
            user, created = User.objects.get_or_create(
                username=pdata['username'],
                defaults={
                    'first_name': pdata['first'],
                    'last_name': pdata['last'],
                    'middle_name': pdata['middle'],
                    'gender': pdata['gender'],
                    'role': 'PLAYER',
                    'email': f"{pdata['username']}@volley.ru",
                    'bio': f"Игрок волейбольной лиги. Позиция: универсал.",
                }
            )
            if created:
                user.set_password('player123')
                user.save()
            players.append(user)

        # Создаём модератора
        mod_user, created = User.objects.get_or_create(
            username='moderator',
            defaults={
                'first_name': 'Модер',
                'last_name': 'Модераторов',
                'role': 'MODERATOR',
                'email': 'moder@volley.ru',
            }
        )
        if created:
            mod_user.set_password('moder123')
            mod_user.save()

        # Даём модератору права на НВЛ
        ModeratorPermission.objects.get_or_create(
            user=mod_user, championship=champ1,
            defaults={'can_edit_teams': True, 'can_edit_matches': True, 'can_edit_players': True}
        )

        # Создаём судью
        ref_user, created = User.objects.get_or_create(
            username='referee',
            defaults={
                'first_name': 'Судья',
                'last_name': 'Судейский',
                'role': 'REFEREE',
                'email': 'ref@volley.ru',
            }
        )
        if created:
            ref_user.set_password('ref123')
            ref_user.save()

        self.stdout.write(f'Создано {len(players)} игроков + модератор + судья')

        # Создаём команды для НВЛ
        team1, _ = Team.objects.get_or_create(championship=champ1, name='Зенит',
                                              defaults={'captain': players[0]})
        team2, _ = Team.objects.get_or_create(championship=champ1, name='Локомотив',
                                              defaults={'captain': players[1]})
        team3, _ = Team.objects.get_or_create(championship=champ1, name='Динамо',
                                              defaults={'captain': players[2]})
        team4, _ = Team.objects.get_or_create(championship=champ1, name='Спартак',
                                              defaults={'captain': players[3]})

        # Добавляем игроков в команды
        positions = ['SETTER', 'OUTSIDE_HITTER', 'OPPOSITE', 'LIBERO', 'MIDDLE_BLOCKER']
        for i, player in enumerate(players[:8]):
            TeamPlayer.objects.get_or_create(
                team=team1 if i < 4 else team2,
                player=player,
                defaults={'jersey_number': i + 1, 'position': positions[i % 5]}
            )

        for i, player in enumerate(players[8:16]):
            TeamPlayer.objects.get_or_create(
                team=team3 if i < 4 else team4,
                player=player,
                defaults={'jersey_number': i + 1, 'position': positions[i % 5]}
            )

        self.stdout.write('Созданы 4 команды с игроками')

        # Создаём матчи и статистику
        now = timezone.now()
        matches_data = [
            {'champ': champ1, 'home': team1, 'away': team2, 'days_ago': 10, 'score': (3, 1)},
            {'champ': champ1, 'home': team3, 'away': team4, 'days_ago': 9, 'score': (2, 3)},
            {'champ': champ1, 'home': team1, 'away': team3, 'days_ago': 5, 'score': (3, 0)},
            {'champ': champ1, 'home': team2, 'away': team4, 'days_ago': 4, 'score': (3, 2)},
            {'champ': champ1, 'home': team1, 'away': team4, 'days_ago': 2, 'score': (0, 3)},
            {'champ': champ1, 'home': team2, 'away': team3, 'days_ago': 1, 'score': (3, 1)},
        ]

        for mdata in matches_data:
            match = Match.objects.create(
                championship=mdata['champ'],
                team_home=mdata['home'],
                team_away=mdata['away'],
                date_time=now - timedelta(days=mdata['days_ago']),
                location='Спорткомплекс "Олимпиец"',
                status='FINISHED',
                score_home=mdata['score'][0],
                score_away=mdata['score'][1],
            )

            # Добавляем статистику для игроков обеих команд
            import random
            for team in [mdata['home'], mdata['away']]:
                for tp in team.players.all():
                    PlayerMatchStats.objects.create(
                        match=match,
                        player=tp.player,
                        points_attack=random.randint(2, 15),
                        points_block=random.randint(0, 5),
                        points_serve=random.randint(0, 4),
                        aces=random.randint(0, 3),
                        blocks=random.randint(0, 4),
                        errors=random.randint(0, 5),
                    )

        self.stdout.write('Созданы 6 матчей со статистикой')
        self.stdout.write('========================================')
        self.stdout.write('Логины и пароли:')
        self.stdout.write('  admin / admin123 (админ)')
        self.stdout.write('  moderator / moder123 (модератор)')
        self.stdout.write('  referee / ref123 (судья)')
        self.stdout.write('  Игроки: ivanov, petrov, ... / player123')
        self.stdout.write('========================================')