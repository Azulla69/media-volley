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
            models.UniqueConstraint(fields=['first_name', 'last_name', 'middle_name', 'birth_date'], name='unique_person')
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


class Award(models.Model):
    """Награда, созданная модератором или админом для турнира"""
    championship = models.ForeignKey('leagues.Championship', on_delete=models.CASCADE, related_name='awards', verbose_name='Чемпионат')
    name = models.CharField(max_length=100, verbose_name='Название')
    detail = models.CharField(max_length=200, blank=True, verbose_name='Описание')
    icon = models.CharField(max_length=10, default='🏅', verbose_name='Иконка')
    color = models.CharField(max_length=20, choices=[
        ('gold', 'Золото'),
        ('silver', 'Серебро'),
        ('bronze', 'Бронза'),
        ('diamond', 'Бриллиант'),
    ], default='gold', verbose_name='Уровень')
    year = models.CharField(max_length=4, blank=True, verbose_name='Год')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Кто создал')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Награда турнира'
        verbose_name_plural = 'Награды турниров'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.championship.name})'


class PlayerAward(models.Model):
    """Выданная награда игроку"""
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='player_awards', verbose_name='Игрок')
    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name='players', verbose_name='Награда')
    awarded_at = models.DateTimeField(auto_now_add=True, verbose_name='Выдана')
    
    class Meta:
        verbose_name = 'Награда игрока'
        verbose_name_plural = 'Награды игроков'
        unique_together = ['player', 'award']
    
    def __str__(self):
        return f'{self.player} — {self.award.name}'
class SiteAward(models.Model):
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_awards', verbose_name='Игрок')
    award_type = models.CharField(max_length=50, verbose_name='Тип награды')
    level = models.CharField(max_length=20, choices=[
        ('bronze', 'Бронза'), ('silver', 'Серебро'), ('gold', 'Золото'), ('diamond', 'Бриллиант')
    ], default='bronze', verbose_name='Уровень')
    value = models.IntegerField(default=0, verbose_name='Значение')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')
    
    class Meta:
        verbose_name = 'Автонаграда'
        verbose_name_plural = 'Автонаграды'
        unique_together = ['player', 'award_type']
    
    def __str__(self):
        return f'{self.player} — {self.award_type} ({self.level})'
    
    def progress_text(self):
        """Возвращает текст прогресса до следующего уровня"""
        thresholds = {
            'matches': [(1, 5, 'bronze'), (5, 10, 'silver'), (10, 50, 'silver'), (50, 100, 'gold'), (100, 500, 'diamond'), (500, None, 'diamond')],
            'bombardier': [(50, 250, 'bronze'), (250, 750, 'silver'), (750, 1500, 'gold'), (1500, None, 'diamond')],
            'attacker': [(30, 150, 'bronze'), (150, 500, 'silver'), (500, 1000, 'gold'), (1000, None, 'diamond')],
            'wall': [(10, 50, 'bronze'), (50, 200, 'silver'), (200, 500, 'gold'), (500, None, 'diamond')],
            'ace_machine': [(15, 75, 'bronze'), (75, 250, 'silver'), (250, 750, 'gold'), (750, None, 'diamond')],
            'recordman': [(25, None, 'gold')],
            'king': [(3, None, 'gold')],
            'captain': [(1, 5, 'bronze'), (5, 25, 'silver'), (25, 100, 'gold'), (100, None, 'diamond')],
            'organizer': [(1, 5, 'bronze'), (5, 15, 'silver'), (15, 50, 'gold'), (50, None, 'diamond')],
            'statistician': [(1, 25, 'bronze'), (25, 100, 'silver'), (100, 350, 'gold'), (350, None, 'diamond')],
            'referee': [(1, 25, 'bronze'), (25, 100, 'silver'), (100, 350, 'gold'), (350, None, 'diamond')],
        }
        rules = thresholds.get(self.award_type, [])
        for min_val, next_val, lvl in rules:
            if self.value >= min_val and self.level == lvl:
                if next_val is None:
                    return 'Макс. уровень'
                remaining = next_val - self.value
                return f'До след. уровня: {remaining}'
        return ''