from django.db import models


class Championship(models.Model):
    LEAGUE_TYPES = [
    ('CLASSIC', 'Классический волейбол'),
    ('BEACH', 'Пляжный волейбол'),
    ('PARK', 'Парковый волейбол'),
]
    
    name = models.CharField(max_length=200, verbose_name='Название чемпионата')
    short_name = models.CharField(max_length=50, verbose_name='Короткое название')
    league_type = models.CharField(max_length=10, choices=LEAGUE_TYPES, verbose_name='Тип волейбола')
    description = models.TextField(verbose_name='Описание')
    about_founders = models.TextField(verbose_name='Об основателях', blank=True)
    
    telegram_link = models.URLField(blank=True, verbose_name='Telegram')
    vk_link = models.URLField(blank=True, verbose_name='ВКонтакте')
    max_link = models.URLField(blank=True, verbose_name='Макс')
    
    logo = models.ImageField(upload_to='championships/logos/', null=True, blank=True, verbose_name='Логотип')
    
    primary_color = models.CharField(max_length=7, default='#1a73e8', verbose_name='Основной цвет')
    secondary_color = models.CharField(max_length=7, default='#ffffff', verbose_name='Вторичный цвет')
    
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