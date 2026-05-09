from django.db import models
from django.conf import settings


class Team(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название команды')
    logo = models.ImageField(upload_to='teams/logos/', null=True, blank=True, verbose_name='Логотип')
    captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='captained_teams', verbose_name='Капитан')
    founder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='founded_teams', verbose_name='Основатель')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'
        ordering = ['name']
    
    def __str__(self):
        return self.name


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
    is_main = models.BooleanField(default=True, verbose_name='Основной состав')
    
    class Meta:
        verbose_name = 'Игрок команды'
        verbose_name_plural = 'Игроки команд'
        unique_together = [['team', 'player'], ['team', 'jersey_number']]
        ordering = ['-is_main', 'jersey_number']
    
    def __str__(self):
        return f'#{self.jersey_number} {self.player} ({self.get_position_display()})'
class TeamInvite(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='invites', verbose_name='Команда')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_invites', verbose_name='Игрок')
    is_main = models.BooleanField(default=True, verbose_name='Основной состав')
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(null=True, default=None)
    
    class Meta:
        verbose_name = 'Приглашение'
        verbose_name_plural = 'Приглашения'
        unique_together = ['team', 'player']