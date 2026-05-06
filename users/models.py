from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Администратор')
        MODERATOR = 'MODERATOR', _('Модератор')
        REFEREE = 'REFEREE', _('Судья')
        STATISTICIAN = 'STATISTICIAN', _('Статист')
        PLAYER = 'PLAYER', _('Игрок')
    
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PLAYER, verbose_name='Роль')
    middle_name = models.CharField(max_length=50, blank=True, verbose_name='Отчество')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Номер телефона')
    city = models.CharField(max_length=100, blank=True, verbose_name='Город')
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', null=True, blank=True, verbose_name='Аватар')
    bio = models.TextField(max_length=500, blank=True, verbose_name='О себе')
    height = models.IntegerField(null=True, blank=True, verbose_name='Рост (см)')
    
    # Соцсети
    vk_link = models.URLField(blank=True, verbose_name='ВКонтакте')
    tg_link = models.URLField(blank=True, verbose_name='Telegram')
    tg_channel = models.URLField(blank=True, verbose_name='Telegram-канал')
    max_link = models.URLField(blank=True, verbose_name='Макс')
    
    GENDER_CHOICES = [('M', 'Мужской'), ('F', 'Женский')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True, verbose_name='Пол')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['last_name', 'first_name']
        constraints = [
            models.UniqueConstraint(fields=['first_name', 'last_name', 'middle_name', 'birth_date'],
                                    name='unique_person')
        ]
    
    def __str__(self):
        if self.middle_name:
            return f'{self.last_name} {self.first_name} {self.middle_name}'
        return f'{self.last_name} {self.first_name}'
    
    @property
    def full_name(self):
        return str(self)


class ModeratorPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderator_permissions', verbose_name='Модератор')
    championship = models.ForeignKey('leagues.Championship', on_delete=models.CASCADE, related_name='moderators', verbose_name='Чемпионат')
    can_edit_teams = models.BooleanField(default=True, verbose_name='Может редактировать команды')
    can_edit_matches = models.BooleanField(default=True, verbose_name='Может редактировать матчи')
    can_edit_players = models.BooleanField(default=True, verbose_name='Может добавлять игроков')
    can_edit_photos = models.BooleanField(default=True, verbose_name='Может редактировать фото')
    
    class Meta:
        verbose_name = 'Права модератора'
        verbose_name_plural = 'Права модераторов'
        unique_together = ['user', 'championship']
    
    def __str__(self):
        return f'{self.user} → {self.championship}'


class StatisticianAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statistician_assignments', verbose_name='Статист')
    match = models.ForeignKey('matches.Match', on_delete=models.CASCADE, related_name='statisticians', verbose_name='Матч')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Назначен')
    
    class Meta:
        verbose_name = 'Назначение статиста'
        verbose_name_plural = 'Назначения статистов'
        unique_together = ['user', 'match']
    
    @property
    def can_edit_until(self):
        return self.match.date_time + timedelta(hours=24)
    
    def __str__(self):
        return f'{self.user} → {self.match}'


class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_sent', verbose_name='Отправитель')
    reported = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received', verbose_name='Нарушитель')
    reason = models.TextField(verbose_name='Причина')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    is_resolved = models.BooleanField(default=False, verbose_name='Решена')
    
    class Meta:
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
    
    def __str__(self):
        return f'Жалоба на {self.reported} от {self.reporter}'