from django.db import models
from django.conf import settings


class Match(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Запланирован'),
        ('LIVE', 'Идёт'),
        ('FINISHED', 'Завершён'),
        ('CANCELLED', 'Отменён'),
    ]
    
    championship = models.ForeignKey('leagues.Championship', on_delete=models.CASCADE, related_name='matches', verbose_name='Чемпионат')
    team_home = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='home_matches', verbose_name='Хозяева')
    team_away = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='away_matches', verbose_name='Гости')
    date_time = models.DateTimeField(verbose_name='Дата и время')
    location = models.CharField(max_length=200, verbose_name='Место проведения')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED', verbose_name='Статус')
    score_home = models.IntegerField(null=True, blank=True, verbose_name='Счёт хозяев')
    score_away = models.IntegerField(null=True, blank=True, verbose_name='Счёт гостей')
    protocol_file = models.FileField(upload_to='protocols/%Y/%m/', null=True, blank=True, verbose_name='Протокол')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_matches', verbose_name='Кто создал')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Матч'
        verbose_name_plural = 'Матчи'
        ordering = ['-date_time']
    
    def __str__(self):
        return f'{self.team_home} vs {self.team_away} ({self.date_time:%d.%m.%Y})'


class PlayerMatchStats(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='player_stats', verbose_name='Матч')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='match_stats', verbose_name='Игрок')
    points_attack = models.IntegerField(default=0, verbose_name='Очки атакой (ОЗ)')
    points_block = models.IntegerField(default=0, verbose_name='Очки блоком (ОБ)')
    points_serve = models.IntegerField(default=0, verbose_name='Очки подачей (ОП)')
    aces = models.IntegerField(default=0, verbose_name='Эйсы')
    blocks = models.IntegerField(default=0, verbose_name='Блоки')
    errors = models.IntegerField(default=0, verbose_name='Ошибки')
    
    class Meta:
        verbose_name = 'Статистика игрока за матч'
        verbose_name_plural = 'Статистика игроков за матчи'
        unique_together = ['match', 'player']
    
    @property
    def total_points(self):
        return self.points_attack + self.points_block + self.points_serve