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
    score_home = models.IntegerField(null=True, blank=True, verbose_name='Партии хозяев')
    score_away = models.IntegerField(null=True, blank=True, verbose_name='Партии гостей')
    protocol_file = models.FileField(upload_to='protocols/%Y/%m/', null=True, blank=True, verbose_name='Протокол')
    protocol_photo = models.ImageField(upload_to='protocols/photos/', null=True, blank=True, verbose_name='Фото протокола')
    stream_link = models.URLField(blank=True, verbose_name='Ссылка на трансляцию')
    video_link = models.URLField(blank=True, verbose_name='Ссылка на запись')
    mvp_home = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='mvp_home_matches', verbose_name='MVP хозяев')
    mvp_away = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='mvp_away_matches', verbose_name='MVP гостей')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_matches', verbose_name='Кто создал')
    created_at = models.DateTimeField(auto_now_add=True)
    reminder_sent = models.BooleanField(default=False, verbose_name='Напоминание отправлено')
    
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
    passes = models.IntegerField(default=0, verbose_name='Передачи (П)')
    points_block = models.IntegerField(default=0, verbose_name='Очки блоком (ОБ)')
    points_serve = models.IntegerField(default=0, verbose_name='Очки подачей (ОП)')
    
    class Meta:
        verbose_name = 'Статистика игрока за матч'
        verbose_name_plural = 'Статистика игроков за матчи'
        unique_together = ['match', 'player']
    
    @property
    def total_points(self):
        return self.points_attack + self.points_block + self.points_serve


class MatchSet(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='sets', verbose_name='Матч')
    set_number = models.IntegerField(verbose_name='Номер партии')
    score_home = models.IntegerField(verbose_name='Очки хозяев')
    score_away = models.IntegerField(verbose_name='Очки гостей')

    class Meta:
        verbose_name = 'Партия'
        verbose_name_plural = 'Партии'
        ordering = ['set_number']
        unique_together = ['match', 'set_number']

    def __str__(self):
        return f'Партия {self.set_number}: {self.score_home}:{self.score_away}'


class MatchReferee(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='referees', verbose_name='Матч')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referee_assignments', verbose_name='Судья')
    is_accepted = models.BooleanField(null=True, default=None, verbose_name='Принял назначение')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Судья матча'
        verbose_name_plural = 'Судьи матчей'
        unique_together = ['match', 'user']

    def __str__(self):
        return f'{self.user} → {self.match}'