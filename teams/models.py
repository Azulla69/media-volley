from django.db import models
from django.conf import settings


class Team(models.Model):
    championship = models.ForeignKey('leagues.Championship', on_delete=models.CASCADE, related_name='teams', verbose_name='Чемпионат')
    name = models.CharField(max_length=100, verbose_name='Название команды')
    logo = models.ImageField(upload_to='teams/logos/', null=True, blank=True, verbose_name='Логотип')
    captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='captained_teams', verbose_name='Капитан')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'
        unique_together = ['championship', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f'{self.name} ({self.championship.short_name})'


class TeamPlayer(models.Model):
    POSITIONS = [
        ('SETTER', 'Связующий'),
        ('OUTSIDE_HITTER', 'Доигровщик'),
        ('OPPOSITE', 'Диагональный'),
        ('LIBERO', 'Либеро'),
        ('MIDDLE_BLOCKER', 'Центральный блокирующий'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players', verbose_name='Команда')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships', verbose_name='Игрок')
    jersey_number = models.IntegerField(verbose_name='Игровой номер')
    position = models.CharField(max_length=20, choices=POSITIONS, verbose_name='Амплуа')
    
    class Meta:
        verbose_name = 'Игрок команды'
        verbose_name_plural = 'Игроки команд'
        unique_together = [['team', 'player'], ['team', 'jersey_number']]
        ordering = ['jersey_number']