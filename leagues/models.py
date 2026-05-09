from django.db import models


class Championship(models.Model):
    LEAGUE_TYPES = [('CLASSIC', 'Классический волейбол'), ('BEACH', 'Пляжный волейбол'), ('PARK', 'Парковый волейбол')]
    STATUS_CHOICES = [('active', 'Активен'), ('recruiting', 'Идёт набор команд'), ('finished', 'Завершён')]
    STAGE_CHOICES = [
        ('applications', 'Сбор заявок'),
        ('review', 'Приём заявок окончен'),
        ('active', 'Идёт'),
        ('finished', 'Завершён'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название чемпионата')
    short_name = models.CharField(max_length=50, blank=True, verbose_name='Короткое название')
    league_type = models.CharField(max_length=10, choices=LEAGUE_TYPES, verbose_name='Тип волейбола')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='applications', verbose_name='Этап')
    description = models.TextField(verbose_name='Описание')
    regulations = models.TextField(blank=True, verbose_name='Положение')
    about_founders = models.TextField(verbose_name='Об основателях', blank=True)
    applications_deadline = models.DateTimeField(null=True, blank=True, verbose_name='Дедлайн заявок')
	
    telegram_link = models.URLField(blank=True, verbose_name='Telegram')
    vk_link = models.URLField(blank=True, verbose_name='ВКонтакте')
    max_link = models.URLField(blank=True, verbose_name='Макс')
    
    logo = models.ImageField(upload_to='championships/logos/', null=True, blank=True, verbose_name='Логотип')
    
    primary_color = models.CharField(max_length=7, default='#1a73e8', verbose_name='Основной цвет')
    secondary_color = models.CharField(max_length=7, default='#ffffff', verbose_name='Вторичный цвет')
    
    is_published = models.BooleanField(default=False, verbose_name='Опубликован')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Чемпионат'
        verbose_name_plural = 'Чемпионаты'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ChampionshipPhoto(models.Model):
    championship = models.ForeignKey(Championship, on_delete=models.CASCADE, related_name='photos', verbose_name='Чемпионат')
    image = models.ImageField(upload_to='championships/photos/', verbose_name='Фотография')
    caption = models.CharField(max_length=200, blank=True, verbose_name='Подпись')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Фотография чемпионата'
        verbose_name_plural = 'Фотографии чемпионатов'
        ordering = ['order']


class Founder(models.Model):
    championship = models.ForeignKey(Championship, on_delete=models.CASCADE, related_name='founders', verbose_name='Чемпионат')
    first_name = models.CharField(max_length=50, verbose_name='Имя')
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')
    bio = models.TextField(max_length=500, blank=True, verbose_name='О себе')
    photo = models.ImageField(upload_to='founders/', null=True, blank=True, verbose_name='Фото')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    
    class Meta:
        verbose_name = 'Основатель'
        verbose_name_plural = 'Основатели'
        ordering = ['order']
    
    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class ChampionshipTeam(models.Model):
    """Заявка команды на участие в чемпионате"""
    championship = models.ForeignKey(Championship, on_delete=models.CASCADE, related_name='applications', verbose_name='Чемпионат')
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='applications', verbose_name='Команда')
    players = models.ManyToManyField('users.User', blank=True, related_name='championship_applications', verbose_name='Игроки в заявке')
    is_approved = models.BooleanField(default=False, verbose_name='Одобрена')
    applied_at = models.DateTimeField(auto_now_add=True, verbose_name='Подана')
    
    class Meta:
        verbose_name = 'Заявка на чемпионат'
        verbose_name_plural = 'Заявки на чемпионаты'
        unique_together = ['championship', 'team']
    
    def __str__(self):
        return f'{self.team.name} → {self.championship.name}'